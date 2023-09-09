(ns framework.server
  (:require
    [promesa.core :as p]
    ["express$default" :as express]
    ["stream" :refer [Readable]]))

(defn str->url [url-str] (js/URL. (str "http://" url-str)))

(defn req->hash-map
  [^js/Object req]
  (let [url (str->url (str (.. req -headers -host) (.-url req)))]
    {:server-port (if-let [port (some-> url
                                        (.-port)
                                        (js/Number))]
                    port
                    80),
     :server-name (.-hostname req),
     :remote-addr (.-ip req),
     :path (.-path req),
     :query-string (.-search url),
     :query (.-query req),
     :scheme (.-protocol req),
     :request-method (keyword (.-method req)),
     :headers (js->clj (.-headers req) :keywordize-keys true),
     :method (keyword (.-method req))
     :body (js->clj (.-body req) :keywordize-keys true)}))

(defn set-headers [res res-map] (.set res (clj->js (:headers res-map))))

(defn set-body
  [res res-map]
  (let [body (:body res-map)]
    (cond
      (instance? Readable body) (.pipe body res)
      body (do
             (.send res body)
             (.end res)))))

(defn server
  [app handler]
  (-> app
      (.disable "x-powered-by")
      (.set "trust proxy" 1)
      (.use (.urlencoded express))
      (.use (fn [req res _next]
              (-> (p/let [req (req->hash-map req)
                          handler (handler)
                          res-map (handler req)]
                    (set-headers res res-map)
                    (.status res (:status res-map 200))
                    (when (:body res-map)
                      (set-body res res-map))
                    #_(.end res))
                  (p/catch (fn [error]
                             (js/console.error error)
                             (.send res (.toString error))
                             (.end res))))))))
