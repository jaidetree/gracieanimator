(ns gracie.data-pipeline
  (:require
    [promesa.core :as p]
    [gracie.queue :as q]
    [gracie.projects2 :as projects]))

(defn load!
  []
  (p/let [[projects] (projects/enqueue-projects)]
    (js/console.log "projects" (count projects))
    (doseq [project projects]
      (js/console.log "name" (get-in project [:properties :type :select :name])))))

(comment
  (load!)
  (println @q/request-cache)
  (p/let [projects (q/do-request {:url "notion-projects"})]
    (println (count projects)))
  (-> (q/resource
        {:requests [{:url "notion-projects"}]
         :on-complete (fn [[projects]]
                        (println "projects resource" (count projects)))})
      (.onValue (fn [] nil))))

