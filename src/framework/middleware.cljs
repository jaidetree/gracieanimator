(ns framework.middleware
  (:require
   [cljs.pprint :refer [pprint]]
   [clojure.string :as s]
   [promesa.core :as p]
   ["fs/promises" :as fs]
   ["path" :as path]
   [reagent.dom.server :as rdom]
   [framework.utils.mime-types :refer [mime-types]]))

(defn wrap-default-view
  []
  (fn [req]
    {:status 404}))

(defn wrap-render-page
  [handler status-pages]
  (fn [req]
    (p/let [res (handler req)]
      (let [status (get res :status 404)]
        (cond (and (<= 200 status) (< status 300) (vector? (:body res)))
              {:headers {:Content-Type "text/html"}
               :status status
               :body (rdom/render-to-string (:body res))}

              (and (<= 200 status) (< status 300))
              res

              (and (<= 300 status) (< status 400))
              res

              :else
              (let [view (get status-pages status)]
                {:headers {:Content-Type "text/html"}
                 :status status
                 :body (rdom/render-to-string (view res (:data res)))}))))))

(defn wrap-error-view
  [handler]
  (fn [req]
    (-> (p/promise (handler req))
        (p/catch
            (fn [error]
              {:status 500
               :data {:error error}})))))

(defn wrap-logging
  [handler]
  (fn [req]
    (pprint req)
    (let [res (handler req)]
      (pprint res)
      res)))

(defn url->filepath
  [root url]
  (let [dirpath (subs url 1)
        dirpath (.replace dirpath "/" (.-sep path))]
    (.resolve path (.join path root dirpath))))

(defn file-exists?
  [filepath]
  (-> (.stat fs filepath)
      (p/then (fn [stats] (.isFile stats)))
      (p/catch (constantly false))))

(defn wrap-static
  [handler root]
  (fn [req]
    (let [filepath (url->filepath root (:uri req))
          ext (subs (.extname path filepath) 1)]
      (p/let [file-exists (file-exists? filepath)]
        (if file-exists
          (p/let [contents (.readFile fs filepath #js {:encoding "utf-8"})
                  content-type (get mime-types ext)]
            {:status 200
             :headers {"Content-Type" content-type}
             :body contents})
          (handler req))))))
