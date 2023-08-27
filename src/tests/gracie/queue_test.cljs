(ns tests.gracie.queue-test
  (:require
    [promesa.core :as p]
    [gracie.queue :as q]
    [cljs.test :as t :refer [async deftest is testing]]))

(deftest enqueue-request-test
  (testing "Can enqueue a request"
    (async done
           (p/do
             (-> (q/enqueue
                   {:type :resource
                    :requests [{:id "https://google.com"
                                :reducer (fn [_ctx res]
                                           res)
                                :fetch (fn []
                                         "content-1")}]})
                 (p/then (fn [text]
                           (is (= text "content-1")))))
             (done)))))

(deftest enqueue-cached-request-test
  (testing "Requests are cached"
    (async done
           (p/do
             (-> (q/enqueue
                   {:type :resource
                    :requests [{:id "https://google.com"
                                :reducer (fn [_ctx res]
                                           res)
                                :fetch (fn []
                                         "content-2")}]})
                 (p/then (fn [text]
                           (is (= text "content-1")))))
             (done)))))
