(ns gracie.dev.server
  (:require
   [clojure.pprint :refer [pprint]]
   [promesa.core :as p]
   [gracie.views.base :refer [base status-pages]]
   [gracie.middleware :as gmw]
   [framework.env :as env]
   [framework.server :refer [server]]
   [framework.middleware :as mw]
   ["express$default" :as express]))

(defonce app-ref (atom nil))


(defn handler
  [req]
  (p/let [f (p/-> (#'mw/wrap-default-view)
                  (#'mw/wrap-file-router "gracie.routes" base)
                  (#'gmw/wrap-fetch-pages)
                  (#'mw/wrap-static "public")
                  (#'mw/wrap-json)
                  (#'mw/wrap-error-view)
                  (#'mw/wrap-render-page status-pages))]
    (f req)))

(defn -main
  []
  (let [app (express)
        port (env/optional :APP_PORT 3000)]
    (doto app
      (server (fn []
                (deref #'handler))))
    (reset! app-ref
            (.listen app port
                     (fn []
                       (println "Server started on port" port))))
    nil))


(defn restart
  []
  (let [app @app-ref]
    (p/-> (p/do! (new js/Promise
                  (fn [resolve _reject]
                    (if app
                      (do (println "Gracefully shutting down server")
                          (.close app resolve))
                      (resolve))))
                 (println "Restarting server")
                 (-main))
          (p/catch
              (fn [err]
                (js/console.error err))))))


(comment
  (let [app @app-ref]
    (.close app (fn []
                  (println "Server closed"))))
  (println "Starting up")
  (-main)
  (restart))
