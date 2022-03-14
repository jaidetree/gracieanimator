(ns gracie.routes.storyboards.index
  (:require
   [clojure.pprint :refer [pprint]]
   [promesa.core :as p]
   [framework.env :as env]
   [framework.utils :as u]
   [notion.api :as notion]
   [gracie.projects.core :as projects]
   [gracie.projects.views :refer [project-thumb]]
   [clojure.string :as s]))

(defn loader
  [_req _data]
  (p/let [categories
          (p/->> (notion/fetch-db-entries
                  {:db-id (env/required "CMS_STORYBOARDS_ID")
                   :filter {:and [{:property "Published"
                                   :checkbox {:equals true}}
                                  {:property "Type"
                                   :select {:equals "Storyboards"}}]}})
                 (projects/format-projects)
                 (projects/sort-newest-first)
                 (projects/group-by-category))]
    {:categories categories}))


(defn view
  [req {:keys [categories]}]
  [:main
   [:h1 "Storyboards"]
   [:div.space-y-16
    (for [[category storyboards] categories]
      [:section.mt-8
       [:h2
        [:a
         {:href (str "/storyboards/category/" (u/slugify category))}
         category]]
       [:ul.flex.flex-wrap.gap-4.mt-8
        (for [storyboard storyboards]
          (let [url (str "/storyboards/"
                         (u/uid->base64 (:uid storyboard))
                         "/" (u/slugify (:title storyboard)))]
            [:li.max-w-xs.w-full
             {:key url}
             [project-thumb
              {:project storyboard
               :url url}
              (:title storyboard)]]))]
       ])]])
