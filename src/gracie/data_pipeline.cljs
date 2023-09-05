(ns gracie.data-pipeline
  (:require
    [clojure.pprint :refer [pprint]]
    [clojure.string :as s]
    [cljs.reader :refer [read-string]]
    [promesa.core :as p]
    [framework.stream :as stream]
    [gracie.queue :as q]
    [gracie.projects2 :as projects]
    [gracie.pages :as pages]
    ["fs/promises" :as fs]
    ["glob" :as glob]))

(def hooks (atom {}))

;; project-types
;; - storyboards
;; - sketchbook-samples
;; - comics
;; - illustrations

;; phases
;; - parse-project
;; - queue-requests
;; - format-project

(defn defhook
  [project-type phase handler]
  (swap! hooks assoc-in [project-type phase] handler))

(defn get-hook
  [project-type phase]
  (get-in @hooks [project-type phase]))

(def cache (atom {:pages []
                  :projects []}))

(comment
  (update-in {} [:storyboards :parse-project] conj 2))

(defn all-projects
  []
  (get @cache :projects []))

(defn all-pages
  []
  (get @cache :pages []))

(defn parse-project
  [project]
  (let [hook-fn (get-hook (:type project) :parse-project)]
    (stream/from-promise
      (p/let [parsed (hook-fn project)]
        {:source   project
         :project  parsed}))))

(defn schedule-requests
  [{:keys [source project] :as state}]
  (let [hook-fn (get-hook (:type source) :queue-requests)]
    (stream/from-promise
     (p/let [requests (hook-fn project)
             ctx (q/enqueue {:type :resource
                             :requests requests})]
       (assoc state
              :requests requests
              :responses ctx)))))

(defn format-project
  [{:keys [source project responses] :as state}]
  (let [hook-fn (get-hook (:type project) :format-project)]
    (stream/from-promise
      (p/let [formatted (hook-fn {:project project
                                  :responses responses})]
        (assoc state :dest formatted)))))

(defn cache-project
  [{:keys [dest] :as state}]
  (stream/from-promise
    (p/let [cached (q/enqueue
                     {:type :cache
                      :data dest})]
      (assoc state :cached cached))))

(defn project-type-supported?
 [project]
 (contains? (set (keys @hooks)) (:type project)))

(defn log-stage
  [stage]
  (fn [state]
   (println "\nStage:" stage (get-in state [:source :title]))
   #_(pprint data)))


(defn projects->project-stream
  [projects]
  (-> (stream/from-seq projects)
      (.map projects/normalize)
      (.filter project-type-supported?)
      (.flatMap parse-project)
      (.doAction (log-stage "parse-project"))
      (.flatMap schedule-requests)
      (.doAction (log-stage "schedule-requests"))
      (.flatMap format-project)
      (.doAction (log-stage "format-project"))
      (.flatMap cache-project)
      (.reduce [] #(conj %1 (:dest %2)))
      (.doAction (log-stage "cache-project"))
      (.doError #(js/console.error %))))

(defn cache-page
  [page]
  (stream/from-promise
    (p/let [cached (q/enqueue
                     {:type :cache
                      :data page})]
      page)))

(defn pages->page-stream
  [pages]
  (-> (stream/from-seq pages)
      (.flatMap cache-page)))

(defn fetch!
 []
 (p/let [[projects pages] (p/all
                            [(projects/enqueue-projects)
                             (pages/enqueue-pages)])]
   (-> (stream/of projects)
       (.flatMap projects->project-stream)
       (.concat (pages->page-stream pages))
       (.doError #(js/console.error %))
       (.toPromise))))

(defn read-cache-file
  [filename]
  (stream/from-promise (.readFile fs filename #js {:encoding "utf-8"})))

(defn group-by-type
  [pages-and-projects]
  (->> pages-and-projects
       (group-by
         #(if (= (:type %) :pages)
            :pages
            :projects))))

(defn read-from-cache
  []
  (let [filesp (.glob glob ".cache/**/*.edn" #js {:ignore ".cache/responses"})]
    (-> (stream/from-promise filesp)
        (.map clj->js)
        (.flatMap stream/from-seq)
        (.flatMap read-cache-file)
        (.map read-string)
        (.reduce [] conj)
        (.doAction
          (fn [files]
            (let [{:keys [projects pages]} (group-by-type files)]
              (reset! cache {:projects projects
                             :pages    pages}))))
        (.toPromise))))


(comment
  (read-from-cache)
  (pprint @cache))

(defn load!
  []
  (p/let [projects (let [projects (all-projects)]
                    (if (empty? projects)
                     (read-from-cache)
                     projects))]
   (if (empty? projects)
    (fetch!)
    projects)))

(defn clear-cache!
  []
  (reset! cache {:projects []
                 :pages []}))

(defn reload!
  []
  (p/do
    (clear-cache!)
    (fetch!)
    (load!)))

(comment
  (p/-> (fetch!)
        (pprint))
  (p/-> (load!)
        (pprint))
  (clear-cache!)
  (load!)
  (pprint @cache)
  ;; @TODO Look into reading requests back from the cache
  (fetch!))


