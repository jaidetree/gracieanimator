(ns tests.cli
  (:require
    [promesa.core :as p]
    #_[tests.gracie.data-pipeline-test]
    #_[tests.gracie.projects-test]
    #_[tests.gracie.queue-test]
    [tests.framework.router-test]
    [cljs.test :as t :refer [async deftest is testing]]))

(defmethod t/report [:cljs.test/default :begin-test-var] [m]
  (println "===" (-> m :var meta :name))
  (println))

(defn -main
  []
  (t/run-all-tests #"^tests\..*-test$"))
