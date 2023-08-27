(ns tests.gracie.data-pipeline-test
  (:require
     [promesa.core :as p]
     [gracie.routes.storyboards.index]
     [gracie.data-pipeline :as dp]
     [cljs.test :as t :refer [async deftest is testing]]))

(deftest defhook-test
  (testing "Can define a hook"
    (dp/defhook :storyboards :parse-project (fn []))
    (is (fn? (get-in @dp/hooks [:storyboards :parse-project])))))

(deftest get-defhook-test
  (testing "Can retrieve a hook fn"
    (dp/defhook :storyboards :parse-project (fn [] :hook-found))
    (is (fn? (dp/get-hook :storyboards :parse-project)))))

