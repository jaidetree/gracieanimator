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

(defonce hooks (atom {}))

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

;; - The fetch function should take a stream
;; - Or a callback function to send a copy of the actions feed to
;; - Replace the log with status message actions
;; - Update fetch to send :init and :complete actions
(def actions (stream/bus))

(def unsub-actions
  (-> actions
      (.onValue #(doto %
                   (println)
                   (js/console.log)))))

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
  [log stage & [extra-fields-fn]]
  (fn [state]
   (log {:type :stage
         :payload (merge
                    {:stage stage
                     :id (get-in state [:source :id])
                     :title (get-in state [:source :title])
                     :type (get-in state [:source :type])}
                    (when extra-fields-fn
                      (extra-fields-fn state)))})))


(defn projects->project-stream
  [projects log]
  (-> (stream/from-seq projects)
      (.map projects/normalize)
      (.filter project-type-supported?)
      (.flatMap parse-project)
      (.doAction (log-stage log "parse-project"))
      (.flatMap schedule-requests)
      (.doAction (log-stage log "schedule-requests"))
      (.flatMap format-project)
      (.doAction (log-stage log "format-project"))
      (.flatMap cache-project)
      (.doAction (log-stage log "cache-project"
                            (fn [state]
                              {:cached (get state :cached)})))
      (.reduce [] #(conj %1 (:dest %2)))
      (.doError #(log {:type :error
                       :payload {:message (.-message %)}}))))

(defn cache-page
  [page]
  (stream/from-promise
    (p/let [cached (q/enqueue
                     {:type :cache
                      :data page})]
      {:page page
       :cached cached})))

(defn pages->page-stream
  [pages log]
  (-> (stream/from-seq pages)
      (.flatMap cache-page)
      (.doAction
        #(log {:type :stage
               :payload {:stage "cache-page"
                         :id (get-in % [:page :id])
                         :title (get-in % [:page :title])
                         :type :page
                         :cached (get-in % [:cached])}}))))


(defn fetch!
 [log]
 (p/let [[projects pages] (p/all
                            [(projects/enqueue-projects)
                             (pages/enqueue-pages)])]
   (log {:type :start
         :payload {:total (+ (* (count projects) 4)
                             (count pages))
                   :projects (count projects)
                   :pages    (count pages)
                   :status "Processing pages and projects..."}})
   (-> (stream/merge-all
         [(projects->project-stream projects log)
          (pages->page-stream pages log)])
       (.doError #(log {:type :error
                        :payload {:message (.-message %)}}))
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
        (.map #(sort-by :order %))
        (.doAction
          (fn [files]
            (let [{:keys [projects pages]} (group-by-type files)]
              (reset! cache {:projects projects
                             :pages    pages}))))
        (.toPromise))))


(comment
  (read-from-cache)
  (pprint @cache))

(defn log
  [action]
  (println action)
  (js/console.log (prn-str action)))

(defn load!
  []
  (p/let [projects (let [projects (all-projects)]
                    (if (empty? projects)
                     (read-from-cache)
                     projects))]
   (if (empty? projects)
    (fetch! log)
    projects)))

(defn clear-cache!
  []
  (reset! cache {:projects []
                 :pages    []}))

(defn reload!
  []
  (p/do
    (clear-cache!)
    (fetch! log)
    (load!)))

(comment
  (p/-> (fetch! log)
        (pprint))
  (p/-> (load!)
        (pprint))
  (pprint @hooks)
  (clear-cache!)
  (load!)
  (reload!)
  (pprint @cache)
  ;; @TODO Look into reading requests back from the cache
  (fetch! log))


