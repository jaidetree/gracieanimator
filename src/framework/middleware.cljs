(ns framework.middleware
  (:require
    [nbb.core :as nbb]
    [cljs.pprint :refer [pprint]]
    [clojure.string :as s]
    [promesa.core :as p]
    ["fs/promises" :as fs]
    ["path" :as path]
    [framework.cookies :as cookies]
    [framework.csrf :as csrf]
    #_[framework.server.router :as router]
    [framework.utils :refer [urlpath->filepath file-exists?]]
    [framework.server.router2 :as router2]
    [reagent.dom.server :as rdom]
    [framework.server.mime-types :refer [mime-types]]))

(defn wrap-default-view
  []
  (fn [req]
    (if (or (:body req)
            (and (get-in req [:headers :Location])
                 (or (= (:status req) 301)
                     (= (:status req) 302))))
      req
      {:status 404})))

(defn wrap-render-page
  [handler status-pages]
  (fn [req]
    (p/let [res (handler req)]
      (let [status (get res :status 404)]
        (cond (and (<= 200 status) (< status 300) (vector? (:body res)))
              {:headers (merge (:headers res)
                               {:Content-Type "text/html"})
               :status status
               :session (:session res)
               :body (rdom/render-to-string (:body res))}
              (and (<= 200 status) (< status 300)) res
              (and (<= 300 status) (< status 400)) res
              :else
              (let [view (get status-pages status)]
                {:headers (merge (:headers res) {:Content-Type "text/html"})
                 :session (:session res)
                 :status status
                 :body (rdom/render-to-string (view res (:data res)))}))))))

(defn wrap-error-view
  [handler]
  (fn [req]
    (-> (p/promise (handler req))
        (p/catch (fn [error] {:status 500, :data {:error error}})))))

(defn wrap-logging
  [handler]
  (fn [req]
    #_(println "->" (:method req) (:path req))
    (p/let [start (js/performance.now)
            res (handler req)
            end  (js/performance.now)]
      (println (:method req) (:path req) (str (.toFixed (- end start) 2) "ms"))
      res)))

(defn wrap-static
  [handler root]
  (fn [req]
    (let [filepath (urlpath->filepath root (:path req))
          ext (subs (.extname path filepath) 1)]
      (p/let [file-exists (file-exists? filepath)]
        (if file-exists
          (p/let [contents (.readFile fs filepath)
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
    (p/let [req (if (json-header? req) (update req :body json->clj) req)
            res (handler req)]
      (if (json-header? res) (update res :body clj->json) res))))

(defn wrap-router
  [handler root-layout-fn routes]
  (router2/route-url
    routes
    (fn [req route]
      (if route
        (p/let [{:keys [view-fn params]} route
                req (assoc req :params params)
                result (view-fn req (:data req {}))]
          (if (map? result) ;; Result was a response object
            (let [req (merge req
                             #_{:status 200
                                :headers (merge (:headers req)
                                                {:Content-Type "text/html"})}
                             result)]
              (if (:view req)
                (handler (assoc req :body (root-layout-fn req (:data req {}) (:view req))))
                (handler req)))
            (handler        ;; Result was a hiccup view
              (merge req
                     {:status  200
                      :headers {:Content-Type "text/html"}
                      :body    (root-layout-fn req (:data req {}) result)}))))
        (handler req)))))

(defn wrap-cookies
  [handler]
  (fn [req]
    (let [cookie-header (get-in req [:headers :cookie])
          session (when cookie-header
                   (cookies/cookie->hash-map cookie-header))
          session (or session {:csrf (csrf/create)})
          req (assoc req :session session)]
      (p/let [res (handler req)]
        (if (:session res)
          (assoc-in res [:headers :Set-Cookie] (cookies/hash-map->cookie (:session res)))
          res)))))

(defn wrap-csrf
  [handler]
  (fn [req]
    (if (contains? #{:POST :PUT :PATCH} (:method req))
      (let [expected-csrf (get-in req [:session :csrf])
            actual-csrf (get-in req [:body :csrf])]
        (if (= expected-csrf actual-csrf)
          (handler (assoc-in req [:session :csrf] (csrf/create)))
          (js/throw (js/Error. "CSRF token failed validation"))))
      (handler req))))

(defn wrap-cache-policy
  [handler]
  (fn [req]
    (p/let [res (handler req)]
      (if (and (contains? #{:POST :PUT :PATCH :DELETE} (:method req))
               (or (not (get-in res [:headers :Cache-Control]))
                   (not (get-in res [:headers "Cache-Control"]))))
        (assoc-in res [:headers :Cache-Control] "no-store")
        res))))
