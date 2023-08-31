(ns gracie.routes.home
  (:require [clojure.string :as s]
            [clojure.pprint :refer [pprint]]
            [framework.utils :as u]
            [gracie.data-pipeline :refer [all-projects]]
            [gracie.projects2 :as projects]
            [gracie.projects.views :refer [project-thumb]]
            [promesa.core :as p]))

(def sort-order
  [:storyboards
   :illustrations
   :sketchbook-samples
   :comics])

(defn view
  [req {:keys [projects]}]
  (let [projects-by-type (projects/group-by-type sort-order projects)]
    [:div.flex.flex-wrap.gap-4.justify-center.md:justify-start
     (for [[type project] (or projects-by-type [])]
       (let [url (str "/" (u/slugify type) "/")]
         [project-thumb {:key (:id project), :url url, :project project} type]))
     #_[:pre (u/pprint-str pages)]]))
