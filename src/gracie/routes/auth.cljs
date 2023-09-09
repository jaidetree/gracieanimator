(ns gracie.routes.auth
  (:require
    [framework.env :as env]
    ["crypto" :as crypto]))

(def expected-password (env/required "GRACIE_STORYBOARDS_PASSWORD"))

(defn post
  [req _data]
  (let [body (:body req)]
    (if (= (:password body) expected-password)
      {:status 301
       :headers {:Location (or (:redirect body) "/")}
       :session (merge (:session req)
                       {:auth (-> (.randomBytes crypto 16) (.toString "hex"))})}
      {:status 302
       :headers {:Location (or (:redirect body) "/")}})))

(defn view
  [req data]
  (case (:method req)
    :POST (post req data)
    {:status 302
     :headers {:Location "/storyboards/"}
     :session (:session req)}))

(defn logout
  [req _data]
  {:status 302
   :headers {:Location "/"}
   :session (dissoc (:session req) :auth)})

