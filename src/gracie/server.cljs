(ns gracie.server
  (:require
    [promesa.core :as p]
    [framework.env :as env]
    [framework.middleware :as mw]
    [framework.server :refer [server]]
    [gracie.data-pipeline :as dp]
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
        (mw/wrap-render-page status-pages)
        (mw/wrap-cookies)
        (mw/wrap-cache-policy)
        (mw/wrap-logging)
        (mw/wrap-error-view)))


(defn -main
  [& _args]
  (dp/load!)
  (let [app (express)
        port (env/required :PORT)]
    (doto app
      (server (constantly handler-promise))
      (.listen port "0.0.0.0"
               (fn []
                 (println "Server started on port" port))))))
