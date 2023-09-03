(ns gracie.routes.deploy
  (:require
    [promesa.core :as p]
    [framework.stream :as stream]
    [framework.env :as env]
    [gracie.data-pipeline :as dp]))

(defonce deploy-bus (stream/bus))

(defn deploy-stream
  [start-time]
  (stream/from-promise
    (p/do
      (dp/fetch!)
      (dp/clear-cache!)
      (dp/load!)
      (let [end-time (js/Date.now)]
        {:start start-time
         :end end-time
         :elapsed (/ (- end-time start-time)
                     1000)}))))

(defonce deploy-pipeline
  (-> deploy-bus
      (.throttle (* 1000 60 2))
      (.flatMap deploy-stream)
      (.onValue println)))

(defn spinner
  []
  [:svg
   {:class "animate-spin h-10 w-10 text-white inline-block"
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

(defn view
  [req {:keys []}]
  (let [deploy-key (get-in req [:params :deploy-key])]
    (if (= deploy-key (env/required "GRACIE_DEPLOY_KEY"))
      (do
        (.push deploy-bus (js/Date.now))
        {:status 200
         :headers {:Refresh "60;/"
                   :Content-Type "text/html"}
         :view
          [:main.text-center.space-y-8
           [spinner]
           [:p
            "Deploy in progress, fetching updated content from CMS. Will redirect once complete, in about 1 minute."]]})
      {:status 302
       :session (:session req)
       :headers {:Location "/"}
       :body "Redirecting"})))
