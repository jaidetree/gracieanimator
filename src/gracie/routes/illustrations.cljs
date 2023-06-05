(ns gracie.routes.illustrations
  (:require [clojure.pprint :refer [pprint]]
            [promesa.core :as p]
            [framework.env :as env]
            [framework.assets :refer [download]]
            [notion.api :as notion]
            [gracie.projects.core :as projects]))


(defn loader
  [_req _data]
  (p/let [illustrations
            (p/->> (notion/fetch-db-entries
                     {:db-id (env/required "CMS_STORYBOARDS_ID"),
                      :filter {:and [{:property "Published",
                                      :checkbox {:equals true}}
                                     {:property "Type",
                                      :select {:equals "Illustrations"}}]}})
                   (projects/format-projects))]
    {:illustrations illustrations}))

(defn view
  [_req {:keys [illustrations]}]
  [:div [:h1.mb-8 "Illustrations"]
   [:div.illustrations.space-y-8
    (for [illustration illustrations]
      [:img
       {:src (download "imgs/illustrations" (:image illustration)),
        :alt (:title illustration)}]) #_[:pre (u/pprint-str illustrations)]]])
