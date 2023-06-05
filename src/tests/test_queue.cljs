(ns tests.test-queue
  (:require
    [clojure.pprint :refer [pprint]]
    [promesa.core :as p]
    [gracie.projects2 :as projects]))


(defn -main
  []
  (p/let [[projects] (projects/enqueue-projects)]
    (println "projects"
             (count projects))
    (pprint (first projects))))


