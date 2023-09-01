(ns framework.server
  (:require
    [promesa.core :as p]
    ["express$default" :as express]))

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

(defn set-body [res res-map] (.send res (:body res-map)))

(defn server
  [app handler]
  (-> app
      (.use (.urlencoded express))
      (.use (fn [req res _next]
              (-> (p/let [req (req->hash-map req)
                          handler (handler)
                          res-map (handler req)]
                    #_(println
                        "RESPONSE:"
                        (select-keys res-map [:headers :status]))
                    (set-headers res res-map)
                    (when (:body res-map)
                      (set-body res res-map))
                    (.status res (:status res-map 200))
                    (.end res))
                  (p/catch (fn [error]
                             (js/console.error error)
                             (.send res (.toString error))
                             (.end res))))))))
