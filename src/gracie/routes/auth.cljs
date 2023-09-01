(ns gracie.routes.auth
  (:require
    [framework.env :as env]
    ["crypto" :as crypto]))

(def expected-password (env/required "GRACIE_STORYBOARDS_PASSWORD"))

(defn handler
  [req]
  (let [body (:body req)]
    (if (= (:password body) expected-password)
      {:status 301
       :headers {:Location (or (:redirect body) "/")}
       :session (merge (:session req)
                       {:auth (-> (.randomBytes crypto 16) (.toString "hex"))})}
      {:status 302
       :headers {:Location (or (:redirect body) "/")}})))
