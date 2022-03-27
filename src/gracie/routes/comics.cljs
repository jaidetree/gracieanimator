(ns gracie.routes.comics
  (:require
   [clojure.pprint :refer [pprint]]
   [promesa.core :as p]
   [framework.env :as env]
   [framework.utils :as u]
   [notion.api :as notion]
   [gracie.projects.core :as projects]
   [clojure.string :as s]))

(defn loader
  [req _data]
  (p/let [illustrations
          (p/->> (notion/fetch-db-entries
                  {:db-id (env/required "CMS_STORYBOARDS_ID")
                   :filter {:and [{:property "Published"
                                   :checkbox {:equals true}}
                                  {:property "Type"
                                   :select {:equals "Comics"}}
                                  ]}})
                 (projects/format-projects))]
    {:illustrations illustrations}))

(defn view
  [req {:keys [illustrations]}]
  [:div
   [:h1.mb-8 "Comics"]
   [:div.comics.space-y-8
    (for [illustration illustrations]
      [:img
       {:src (:image illustration)}])

    #_[:pre
     (u/pprint-str illustrations)]]])
