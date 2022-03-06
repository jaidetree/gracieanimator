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
  [status-pages]
  (fn [req]
    (let [status (get req :status 404)
          view (get status-pages status)]
      {:headers {:content-type "text/html"}
       :status status
       :body (rdom/render-to-string (view req (:data req)))})))

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
            {:headers {"Content-Type" content-type}
             :body contents})
          (handler req))))))
