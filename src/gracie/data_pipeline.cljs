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

(defn get-hook
  [project-type phase]
  (get-in @hooks [project-type phase]))

(def projects-queue (stream/bus))

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
              responses (q/enqueue {:type :resource
                                    :requests requests})]
        (assoc state
               :requests requests
               :responses responses)))))


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
      (.onValue js/console.log)))

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


