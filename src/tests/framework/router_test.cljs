(ns tests.framework.router-test
  (:require
     [promesa.core :as p]
     [framework.server.router2 :as router]
     [gracie.routes :refer [routes]]
     [cljs.test :as t :refer [async deftest is testing]]))

(deftest match-paths-test
  (testing "Can match static urls"
    (let [expected '("storyboards" "category" "action-adventure")
          actual '("storyboards" "category" "action-adventure")]
      (is (= (router/match-paths actual expected) {:params {}})))))

(deftest match-paths-params-test
  (testing "Can extract dynamic params"
    (let [expected '("comics" ":slug")
          actual '("comics" "29-dumpling-the-eternal")]
      (is (= (router/match-paths actual expected) {:params {:slug "29-dumpling-the-eternal"}})))))

(deftest route-url-static-test
  (testing "Can match static routes"
    (let [routes {"/illustrations/" (fn [])
                  "/comics/"        (fn [])
                  "/comics/:slug/"  (fn [])}
          route-fn (router/route-url
                     routes
                     (fn [req match]
                       (is (= (:params match) {}))))]
      (route-fn
        {:path "/comics/"}))))

(deftest route-url-dynamic-test
  (testing "Can match dynamic routes"
    (let [routes {"/illustrations/" (fn [])
                  "/comics/"        (fn [])
                  "/comics/:slug/"  (fn [])}
          route-fn (router/route-url
                     routes
                     (fn [req match]
                       (is (= (:params match) {:slug "29-dumpling-the-eternal"}))))]
      (route-fn
        {:path "/comics/29-dumpling-the-eternal/"}))))

(deftest route-url-routes-test
  (testing "Can match dynamic routes"
    (let [route-fn (router/route-url
                     routes
                     (fn [req match]
                       (println match)
                       (is (= (:params match)
                              {:slug "29-dumpling-the-eternal"}))))]
      (route-fn
        {:path "/comics/29-dumpling-the-eternal/"}))))
