(ns gracie.server
  (:require
    [promesa.core :as p]
    [framework.env :as env]
    [framework.middleware :as mw]
    [framework.server :refer [server]]
    [gracie.middleware :as gmw]
    [gracie.routes :refer [routes]]
    [gracie.views.base :refer [base status-pages]]
    ["express$default" :as express]))

(def handler-promise
  (p/-> (mw/wrap-default-view)
        (mw/wrap-router base routes)
        (gmw/wrap-dynamic-page-router)
        (gmw/wrap-data)
        (mw/wrap-csrf)
        (mw/wrap-static "public")
        (mw/wrap-json)
        (mw/wrap-error-view)
        (mw/wrap-render-page status-pages)
        (mw/wrap-cookies)
        (mw/wrap-cache-policy)
        (mw/wrap-logging)))

(defn -main
  [& _args]
  (let [app (express)
        port (env/required :PORT)]
    (doto app
      (server (fn [req]
                (p/let [handler handler-promise]
                  (handler req))))
      (.listen port
               (fn []
                 (println "Server started on port" port))))))
