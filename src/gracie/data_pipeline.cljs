(ns gracie.data-pipeline
  (:require
    [clojure.pprint :refer [pprint]]
    [promesa.core :as p]
    [framework.stream :as stream]
    [gracie.queue :as q]
    [gracie.projects2 :as projects]
    ["fs/promises" :as fs]))

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

(def projects-queue (stream/bus))

(defn parse-project
  [project])

(defn schedule-requests
  [project])

(defn format-project
  [project])

(defn cache-project
  [project])

(defn projects->project-stream
  [projects]
  (-> (stream/from-seq projects)
      (.flatMap parse-project)
      (.flatMap schedule-requests)
      (.format format-project)
      (.flatMap cache-project)))

(def projects-pipeline
  (-> projects-queue
      (.flatMapLatest projects->project-stream)
      (.onValue console.log)))

(defn load!
 []
 (p/let [[projects] (projects/enqueue-projects)
         projects (map projects/normalize projects)]
   (js/console.log "projects" (count projects))
   (.writeFile fs "debug/project.edn"
               (with-out-str
                 (pprint (first projects)))
               #js {:encoding "utf-8"})
   (doseq [project projects]
     nil)))

(comment
  (load!)
  (println @q/request-cache)
  (p/let [projects (q/do-request {:url "notion-projects"})]
    (js/console.log (count projects)))
  (-> (q/resource
        {:requests [{:url "notion-projects"}]
         :on-complete (fn [[projects]]
                        (println "projects resource" (count projects)))})
      (.onValue (fn [] nil))))


