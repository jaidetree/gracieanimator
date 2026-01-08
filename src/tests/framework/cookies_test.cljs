(ns tests.framework.cookies-test
  (:require
   [promesa.core :as p]
   [framework.cookies :as cookies]
   [cljs.test :as t :refer [async deftest is testing]]))

(deftest encrypt-test
  (testing "Can encrypt data"
    (is (= (cookies/hash-map->cookie {:test "hello-world"}) "test"))))

