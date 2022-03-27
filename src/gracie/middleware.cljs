(ns gracie.middleware
  (:require
   [clojure.pprint :refer [pprint]]
   [promesa.core :as p]
   [notion.api :as notion]
   [framework.env :as env]))

(defn format-page
  [page]
  (let [props (get page :properties {})]
    {:id (get page :id)
     :slug (get-in props [:url-friendly-name :rich-text 0 :text :content])
     :title (get-in props [:name :title 0 :text :content])}))


(defn wrap-fetch-pages
  [handler]
  (fn [req]
    (p/let [pages (p/->> (notion/fetch-db-entries
                          {:db-id (env/required "CMS_PAGES_ID")
                           :filter {:and [{:property "Published"
                                           :checkbox {:equals true}}
                                          ]}
                           :sorts [{:property "Order"
                                    :direction "ascending"}]})
                         (map format-page)
                         (p/all))]
      (handler (assoc-in req [:data :pages] pages)))))
