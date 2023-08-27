(ns tests.cli
  (:require
    [promesa.core :as p]
    [tests.gracie.data-pipeline-test]
    [tests.gracie.projects-test]
    [tests.gracie.queue-test]
    [cljs.test :as t :refer [async deftest is testing]]))

(defmethod t/report [:cljs.test/default :begin-test-var] [m]
  (println "===" (-> m :var meta :name))
  (println))

(defn -main
  []
  (t/run-all-tests #"tests\.gracie\..*"))
