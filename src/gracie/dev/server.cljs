(ns gracie.dev.server
  (:require
    [clojure.pprint :refer [pprint]]
    [promesa.core :as p]
    [gracie.views.base :refer [base status-pages]]
    [gracie.routes :refer [routes]]
    [gracie.data-pipeline :as dp]
    [framework.env :as env]
    [framework.server :refer [server]]
    [framework.middleware :as mw]
    [framework.utils :as u]
    ["express$default" :as express]))

(defonce app-ref (atom nil))

(defn wrap-data
  [handler]
  (fn [req]
    (handler (-> req
                 (assoc-in [:data :projects] (dp/all-projects))
                 (assoc-in [:data :pages] (dp/all-pages))))))

(defn wrap-dynamic-page-router
  [handler]
  (fn [req]
    (let [path-slug (u/slugify (:path req))
          pages (get-in req [:data :pages])
          page (->> pages
                    (some #(when (= (:slug %) path-slug) %)))]
      (if page
        {:headers (assoc (:headers req)
                         :Content-Type "text/html")
         :session (:session req)
         :status 200
         :body
         (base
           req (:data req)
           [:div
            [:h1.mb-8
             (:title page)]
            (into [:div] (:content page))])}
        (handler req)))))


(defn handler
  [req]
  (p/let [f (p/-> (#'mw/wrap-default-view)
                  (#'mw/wrap-router base routes)
                  (#'wrap-dynamic-page-router)
                  (#'wrap-data)
                  (#'mw/wrap-csrf)
                  (#'mw/wrap-static "public")
                  (#'mw/wrap-json)
                  (#'mw/wrap-error-view)
                  (#'mw/wrap-render-page status-pages)
                  (#'mw/wrap-cookies)
                  (#'mw/wrap-cache-policy)
                  #_(#'mw/wrap-logging))]
    (f req)))

(defn -main
  []
  (let [app (express)
        port (env/optional :APP_PORT 3000)]
    (doto app (server (fn [] (deref #'handler))))
    (reset! app-ref (.listen app
                             port
                             (fn [] (println "Server started on port" port))))
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
          (p/catch (fn [err] (js/console.error err))))))

(dp/load!)

(comment
  (let [app @app-ref] (.close app (fn [] (println "Server closed"))))
  (println "Starting up")
  (-main)
  (restart))
