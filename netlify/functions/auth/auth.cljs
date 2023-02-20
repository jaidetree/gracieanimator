(ns functions.auth
  (:require
   [promesa.core :as p]
   ["fs/promises" :as fs]
   ["jsonwebtoken$default" :as jwt]))

(defn create-jwt
  [password]
  (.sign jwt (clj->js {:authorized true}) password))

(defn handler
  [event ctx]
  (let [body (js->clj (js/JSON.parse (.-body event)) :keywordize-keys true)]
    (if (= (:password body) js/process.env.GRACIE_STORYBOARDS_PASSWORD)
      (p/let [contents (.readFile fs "./netlify/functions/auth/storyboards.html" #js {:encoding "utf-8"})]
        (clj->js {:statusCode 200
                  :body (js/JSON.stringify #js {:status "ok"
                                                :token (create-jwt (:password body))
                                                :contents contents})}))
      (clj->js {:statusCode 400
                :body (js/JSON.stringify #js {:status "fail"
                                              :message "Unauthorized"})}))))

;; Exports
#js {:handler handler}
