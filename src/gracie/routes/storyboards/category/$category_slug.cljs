(ns gracie.routes.storyboards.category.$category-slug
  (:require
   [clojure.pprint :refer [pprint]]
   [framework.env :as env]
   [framework.utils :as u]
   [notion.api :as notion]
   [promesa.core :as p]
   [gracie.projects.core :as projects]
   [clojure.string :as s]))


(defn loader
  [req _data]
  (let [slug (-> req
                 (get-in [:params :category-slug]))]
    (p/let [db       (notion/fetch-db {:db-id (env/required "CMS_STORYBOARDS_ID")})
            categories (projects/db->categories db)
            category (projects/find-category categories slug)
            projects (p/->> (notion/fetch-db-entries
                             {:db-id (env/required "CMS_STORYBOARDS_ID")
                              :filter {:and [{:property "Published"
                                              :checkbox {:equals true}}
                                             {:property "Type"
                                              :select {:equals "Storyboards"}}
                                             {:property "Category"
                                              :select {:equals category}}
                                             ]}})
                            (projects/format-projects)
                            (projects/sort-newest-first))]
      {:storyboards projects
       :categories  categories
       :category    category})))


(defn view
  [req {:keys [storyboards categories category]}]

  [:main
   [:h1
    [:a
     {:href "/storyboards"}
     "Storyboards"]]
   [:p.uppercase.font-body
    category]
   [:ul.flex.flex-wrap.gap-4.mt-8
    (for [storyboard storyboards]
      (let [url (str "/storyboards/"
                     (u/uid->base64 (:uid storyboard))
                     "/" (u/slugify (:title storyboard)))]
        [:li.max-w-xs.w-full
         [:div.text-center
          [:div.relative.overflow-hidden
           {:style {:height "13.5rem"}}
           [:a.absolute.left-0.right-0.top-0.bottom-0.block
            {:href url
             :style {:background-image (str "url('"
                                            (or (get storyboard :image)
                                                (get-in storyboard [:video :thumbnail_url]))
                                            "')")
                     :background-repeat "no-repeat"
                     :background-size   "cover"
                     :background-position "center"}}]]
          [:h2.text-base.font-body.font-light
           [:a
            {:href url}
            (:title storyboard)]]]]))]])
