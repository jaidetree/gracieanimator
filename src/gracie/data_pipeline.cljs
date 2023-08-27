(ns gracie.data-pipeline
  (:require
    [clojure.pprint :refer [pprint]]
    [cljs.reader :refer [read-string]]
    [promesa.core :as p]
    [framework.stream :as stream]
    [gracie.queue :as q]
    [gracie.projects2 :as projects]
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

(def projects-cache (atom []))

(comment
  (update-in {} [:storyboards :parse-project] conj 2))

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

(defn log-stage
  [stage]
  (fn [data]
   (println "\nStage:" stage)
   #_(pprint data)))

(defn projects->project-stream
  [projects]
  (-> (stream/from-seq projects)
      (.take 1)
      (.flatMap parse-project)
      #_(.doAction (log-stage "parse-project"))
      (.flatMap schedule-requests)
      #_(.doAction (log-stage "schedule-requests"))
      (.flatMap format-project)
      #_(.doAction (log-stage "format-project"))
      (.flatMap cache-project)
      (.reduce [] #(conj %1 (:dest %2)))
      #_(.doAction (log-stage "cache-project"))
      (.doError js/console.error)))


(defn fetch!
 []
 (p/let [projects (projects/enqueue-projects)]
  (->> projects
       (map projects/normalize)
       (projects->project-stream)
       (.toPromise))))

(defn read-cache-file
  [filename]
  (stream/from-promise (.readFile fs filename #js {:encoding "utf-8"})))

(defn read-from-cache
  []
  (let [filesp (.glob glob ".cache/**/*.edn")]
    (-> (stream/from-promise filesp)
        (.map clj->js)
        (.flatMap stream/from-seq)
        (.flatMap read-cache-file)
        (.map read-string)
        (.reduce [] conj)
        (.doAction #(reset! projects-cache %))
        (.toPromise))))


(comment
  (read-from-cache)
  (println @projects-cache))

(defn load!
  []
  (p/let [projects (let [projects @projects-cache]
                    (if (empty? projects)
                     (read-from-cache)
                     projects))]
   (if (empty? projects)
    (fetch!)
    projects)))

(comment
  (p/-> (fetch!)
        (pprint))
  (p/-> (load!)
        (pprint))
  ;; @TODO Look into reading requests back from the cache
  (fetch!))


