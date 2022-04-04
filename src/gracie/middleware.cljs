(ns gracie.middleware
  (:require
   [clojure.pprint :refer [pprint]]
   [promesa.core :as p]
   [notion.api :as notion]
   [framework.env :as env]
   [gracie.projects.core :as projects]))


(defn wrap-fetch-pages
  [handler]
  (fn [req]
    (p/let [pages (projects/fetch-pages)]
      (handler (assoc-in req [:data :pages] pages)))))
