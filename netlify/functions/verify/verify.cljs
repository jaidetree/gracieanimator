(ns functions.verify
  (:require
   [promesa.core :as p]
   ["fs/promises" :as fs]
   ["jsonwebtoken$default" :as jwt]))

(defn handler
  [event ctx]
  (let [body (js->clj (js/JSON.parse (.-body event)) :keywordize-keys true)
        token (:token body)]
    (try
      (.verify jwt token js/process.env.GRACIE_STORYBOARDS_PASSWORD)
      (p/let [contents (.readFile fs "./netlify/functions/auth/storyboards.html" #js {:encoding "utf-8"})]
        (clj->js {:statusCode 200
                  :body (js/JSON.stringify #js {:status "ok"
                                                :token token
                                                :contents contents})}))
      (catch js/Error error
        (clj->js {:statusCode 400
                  :body (js/JSON.stringify #js {:status "fail"
                                                :message "Unauthorized"})})))))

;; Exports
#js {:handler handler}
