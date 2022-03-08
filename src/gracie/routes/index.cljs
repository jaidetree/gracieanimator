(ns gracie.routes.index
  (:require
   [clojure.pprint :refer [pprint]]
   [framework.env :as env]
   [framework.utils :refer [pprint-str read-edn-file]]
   [notion.api :as notion]
   [promesa.core :as p]
   ["node-fetch$default" :as fetch]))

(defn format-pdf
  [file]
  {:name (get file :name)
   :url  (get-in file [:file :url])})

(defn format-storyboard
  [storyboard]
  (let [fields (get storyboard :properties)]
    {:id (get storyboard :id)
     :pdfs (->> (get-in fields [:PDF :files])
                (map format-pdf))
     :image (->> (get-in fields [:Image :files])
                 (map #(get-in % [:file :url]))
                 (first))
     :vimeo-url (get-in fields [:URL :url])
     :type (get-in fields [:Type :select :name])
     :category (get-in fields [:Category :select :name])
     :tags     (->> (get-in fields [:Tags :multi_select])
                    (map #(select-keys % [:id :name])))
     :featured (get-in fields [:Featured :checkbox])
     :title    (get-in fields [:Name :title 0 :text :content])
     :updated-at (get storyboard :last_edited_time)}))

(defn format-storyboards
  [storyboards]
  (->> storyboards
       (map format-storyboard)))

(defn fetch-vimeo-oembed
  [url]
  (let [vimeo-api-url (str "https://vimeo.com/api/oembed.json?url="
                           (js/encodeURIComponent url)
                           "&width=1280&height=720")
        params (clj->js {:headers {"Referer" "https://gracieanimator.squarespace.com"}})]
    (-> (p/-> (fetch vimeo-api-url params)
              (.json)
              (js->clj :keywordize-keys true))
        (p/catch
            (fn [error]
              (println "error fetching" vimeo-api-url)
              (js/console.error error)
              {})))))

(defn fetch-video
  [project]
  (if (= (:type project) "Storyboards")
    (p/let [video (fetch-vimeo-oembed (get project :vimeo-url))]
      (assoc project :video video))
    project))

(defn fetch-videos
  [storyboards]
  (->> storyboards
       (map fetch-video)))

(defn category-order
  [[type _projects]]
  (case type
    "Storyboards"        0
    "Illustrations"      1
    "Sketchbook Samples" 2
    "Comics"             3
    99))

(defn loader
  []
  (p/let [projects (notion/fetch-db-entries
                       {:db-id (env/required "CMS_STORYBOARDS_ID")
                        :query {:filter {:and [{:property "Published"
                                                :checkbox {:equals true}}
                                               #_{:property "Type"
                                                :select {:equals "storyboard"}}]}}})
          projects (format-storyboards projects)
          projects (p/all (fetch-videos projects))
          projects (sort-by :updated_at #(compare %2 %1) projects)
          project-types (group-by :type projects)
          project-types (sort-by category-order project-types)]
    {:project-types project-types}))

(defn view
  [req {:keys [project-types]}]
  [:div.flex.flex-wrap.gap-4
   (for [[type projects] project-types]
     (let [project (->> projects
                        (filter :featured)
                        (first))]
       [:div.max-w-xs.w-full
        {:key (:id project)}
        [:div.text-center
         [:div.relative.overflow-hidden
          {:style {:height "13.5rem"}}
          [:div.absolute.left-0.right-0.top-0.bottom-0
           {:style {:background-image (str "url('"
                                           (or (get project :image)
                                               (get-in project [:video :thumbnail_url]))
                                           "')")
                    :background-repeat "no-repeat"
                    :background-size   "cover"
                    :background-position "center"}}]]
         [:h2.uppercase.text-lg.font-body.font-light type]]]))
   #_[:pre
    (pprint-str project-types)]])
