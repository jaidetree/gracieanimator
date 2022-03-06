(ns gracie.dev.server (:require
   [promesa.core :as p]
   [gracie.env :as env]
   [gracie.views.base :refer [status-pages]]
   [framework.server :refer [server]]
   [framework.middleware :as mw]
   ["express$default" :as express]))

(defonce app-ref (atom nil))

(def handler
  (p/-> (mw/wrap-default-view status-pages)
        (mw/wrap-static "public")))

(defn -main
  []
  (let [app (express)
        port (env/optional :APP_PORT 3000)]
    (doto app
      (server handler))
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
