(ns tests.gracie.projects-test
  (:require
    [promesa.core :as p]
    [gracie.projects2 :as projects]
    [cljs.test :as t :refer [async deftest is testing]]))

(deftest enqueue-projects
  (testing "Can fetch projects"
    (async
      done
      (p/let [[projects] (projects/enqueue-projects)]
        (is (> (count projects) 10))
        (done)))))


