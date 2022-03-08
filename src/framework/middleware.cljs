(ns framework.middleware
  (:require
   [nbb.core :as nbb]
   [cljs.pprint :refer [pprint]]
   [clojure.string :as s]
   [promesa.core :as p]
   ["fs/promises" :as fs]
   ["path" :as path]
   [reagent.dom.server :as rdom]
   [framework.server.mime-types :refer [mime-types]]))

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

(defn json-header?
  [req]
  (= (get-in req [:headers "Content-Type"]) "application/json"))

(defn json->clj
  [body]
  (-> body
      (js/JSON.parse)
      (js->clj :keywordize-keys true)))

(defn clj->json
  [body]
  (-> body
      (clj->js)
      (js/JSON.stringify nil 2)))

(defn wrap-json
  [handler]
  (fn [req]
    (p/let [req (if (json-header? req)
                  (update req :body json->clj)
                  req)
            res (handler req)]
      (if (json-header? res)
        (update res :body clj->json)
        res))))

(defn url->cljs-path
  [root url]
  (let [filepath (subs url 1)
        filepath (.replace filepath "/" ".")]
    (str root "." filepath)))

(defn- load-data
  [req loader-fn]
  (if loader-fn
    (p/let [data (loader-fn req (:data req))]
      (update req :data merge data))
    req))

(defn- load-meta
  [req meta-fn]
  (if meta-fn
    (p/let [meta (meta-fn req (:data req))]
      (update req :meta merge meta))
    req))

(defn wrap-file-router
  [handler root base-view]
  (fn [req]
    (let [uri (:uri req)
          uri (if (= uri "/") "/index" uri)
          fileroot (.join path "src" (.replace root "." (.-sep path)))
          filepath (str (url->filepath fileroot uri) ".cljs")
          classpath (url->cljs-path root uri)]
      (p/let [file-exists (file-exists? filepath)]
        (if file-exists
          (p/let [module (nbb/load-file filepath)
                  meta-fn (resolve (symbol classpath "meta"))
                  loader-fn (resolve (symbol classpath "loader"))
                  view-fn (resolve (symbol classpath "view"))
                  req (p/-> req
                            (load-data loader-fn)
                            (load-meta meta-fn))]
            {:status 200
             :body (base-view req (:data req)
                              (view-fn req (:data req)))})
          (handler req))))
    ))
