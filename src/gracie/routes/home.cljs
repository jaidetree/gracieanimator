(ns gracie.routes.home
  (:require [clojure.string :as s]
            [clojure.pprint :refer [pprint]]
            [framework.env :as env]
            [framework.utils :as u]
            [gracie.projects.core :as projects]
            [gracie.projects.views :refer [project-thumb]]
            [notion.api :as notion]
            [promesa.core :as p]))

(defn save-snapshot
  [projects]
  (u/write-edn-file "projects.edn" projects)
  projects)

(defn loader
  [req]
  (p/let [projects-by-type (p/->> (notion/fetch-db-entries
                                    {:db-id (env/required "CMS_STORYBOARDS_ID"),
                                     :filter {:and [{:property "Published",
                                                     :checkbox {:equals true}}
                                                    {:property "Featured",
                                                     :checkbox {:equals
                                                                  true}}]}})
                                  (projects/format-projects)
                                  (projects/sort-newest-first)
                                  (projects/group-by-type)
                                  (projects/sort-types))]
    {:projects-by-type projects-by-type}))

(defn view
  [req {:keys [projects-by-type pages]}]
  (println "rendering view")
  [:div.flex.flex-wrap.gap-4.justify-center.md:justify-start
   (for [[type projects] (or projects-by-type [])]
     (let [project (first projects)
           url (str "/" (u/slugify type) "/")]
       [project-thumb {:key (:id project), :url url, :project project} type]))
   #_[:pre (u/pprint-str pages)]])
