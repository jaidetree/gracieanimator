(ns gracie.routes.deploy
  (:require
   [promesa.core :as p]
   [framework.stream :as stream]
   [framework.env :as env]
   [gracie.data-pipeline :as dp]))

(def deploy-bus (stream/bus))
(def action-log-ref (atom nil))

(defn subscribe-to-log
  [action-log]
  (-> action-log
      (.onValue
       (fn [event]
         (prn event)
         #_(js/console.log (prn-str event))))))

(defn deploy-stream
  [start-time]
  (let [action-log (stream/bus)
        log #(.push action-log %)]
    (reset! action-log-ref action-log)
    (log {:type :init
          :payload {:start start-time
                    :status "Deploy started..."}})
    (subscribe-to-log action-log)
    (stream/from-promise
     (p/do
       (dp/fetch! log)
       (log {:type :status
             :payload "Fetched and stored all pages and projects"})
       (dp/clear-cache!)
       (log {:type :status
             :payload "Cleared previous cache of content"})
       (dp/load!)
       (log {:type :status
             :payload "Loaded updated pages and projects into cache"})
       (let [end-time (js/Date.now)]
         (log
          {:type :complete
           :payload {:start start-time
                     :end end-time
                     :elapsed (/ (- end-time start-time)
                                 1000)
                     :status "Update complete! Redirecting to updated home page in 5 seconds."}})
         (.end action-log)
         (reset! action-log-ref nil))))))

(def deploy-pipeline
  (-> deploy-bus
      (.filter #(= (env/optional :NODE_ENV "development") "production"))
      #_(.throttle (* 1000 60 2))
      (.flatMapFirst deploy-stream)
      (.onValue println)))

(comment
  (= (env/optional :NODE_ENV "development") "production")
  (set! (.-NODE_ENV js/process.env) "production"))

(defn spinner
  []
  [:svg
   {:id "spinner"
    :class "animate-spin h-10 w-10 text-white inline-block"
    :xmlns "http://www.w3.org/2000/svg"
    :fill "none"
    :viewBox "0 0 24 24"}
   [:circle
    {:class "opacity-25"
     :cx "12"
     :cy "12"
     :r "10"
     :stroke "currentColor"
     :strokeWidth "4"}]
   [:path
    {:class "opacity-75"
     :fill "currentColor"
     :d "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"}]])

(defn progress-bar
  []
  [:div.hidden.mx-8
   {:id "progress-bar"}
   [:div.relative.rounded-full.w-full.h-5.overflow-hidden
    {:class "bg-black/20"}
    [:div.bg-white.rounded-full.absolute.top-px.left-px.bottom-px.right-px.w-0
     {:id "progress"}]]])

(defn view
  [req {:keys []}]
  (let [deploy-key (get-in req [:params :deploy-key])]
    (if (= deploy-key (env/required "GRACIE_DEPLOY_KEY"))
      (do
        (.push deploy-bus (js/Date.now))
        {:status 200
         :title "Deploy"
         :headers (merge {:Content-Type "text/html"})
         :scripts [{:src "https://cdn.jsdelivr.net/npm/baconjs@3.0.17/dist/Bacon.min.js"
                    :type "application/javascript"}
                   {:src "/cljs/deploy.cljs"
                    :type "application/x-scittle"}]
         :view
         [:main.text-center.space-y-8
          [spinner]
          [progress-bar]
          [:p
           {:id "status"}
           "Fetching pages and projects..."]
          [:div.text-left
           [:pre
            [:code#log.block.text-xs.h-80.overflow-auto]]]]})

      {:status 302
       :session (:session req)
       :headers {:Location "/"}})))

(defn serialize-action
  [action]
  (str "data: " (pr-str action) "\n\n"))

(defn log-view
  [req {:keys []}]
  (if-let [action-log @action-log-ref]
    {:status 200
     :headers {:Cache-Control "no-store"
               :Content-Type  "text/event-stream"}
     :body (-> action-log
               (.map serialize-action)
               (stream/to-readable))}
    {:status 200
     :headers {:Cache-Control "no-store"
               :Content-Type  "text/event-stream"
               :Connnection   "keep-alive"}
     :body (-> (stream/of {:type :end :message "Deploy is not in-progress"})
               (.map serialize-action)
               (stream/to-readable))}))

(comment
  js/process.env.NODE_ENV
  (set! (.-NODE_ENV js/process.env)
        "development")
  (set! (.-NODE_ENV js/process.env)
        "production"))
