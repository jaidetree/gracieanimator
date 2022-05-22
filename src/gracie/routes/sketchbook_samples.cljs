(ns gracie.routes.sketchbook-samples
  (:require
   [clojure.pprint :refer [pprint]]
   [promesa.core :as p]
   [framework.env :as env]
   [framework.assets :refer [download-sync]]
   [framework.utils :as u]
   [notion.api :as notion]
   [gracie.projects.core :as projects]
   [clojure.string :as s]))

(defn loader
  [req _data]
  (p/let [images
          (p/->> (notion/fetch-db-entries
                  {:db-id (env/required "CMS_STORYBOARDS_ID")
                   :filter {:and [{:property "Published"
                                   :checkbox {:equals true}}
                                  {:property "Type"
                                   :select {:equals "Sketchbook Samples"}}
                                  ]}})
                 (projects/format-projects))]
    {:images images}))

(defn view
  [req {:keys [images]}]
  [:div
   [:h1.mb-8 "Sketchbook Samples"]
   [:div.sketchbook-samples.space-y-8
    (for [image images]
      [:img
       {:src (download-sync "imgs/sketchbook-samples" (:image image)) :alt (:title image)}])

    #_[:pre
     (u/pprint-str illustrations)]]])
