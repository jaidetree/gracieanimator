(ns gracie.projects.core
  (:require
   [promesa.core :as p]
   [framework.utils :as u]
   ["node-fetch$default" :as fetch]
   ))


(defn format-pdf
  [file]
  {:name (get file :name)
   :url  (get-in file [:file :url])})

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
              (js/console.error error)
              {})))))

(defn fetch-video
  [vimeo-url]
  (if vimeo-url
    (fetch-vimeo-oembed vimeo-url)
    nil))

(defn fetch-speakerdeck-oembed
  [url]
  (let [vimeo-api-url (str "https://speakerdeck.com/oembed.json?url="
                           (js/encodeURIComponent url))]
    (-> (p/-> (fetch vimeo-api-url)
              (.json)
              (js->clj :keywordize-keys true))
        (p/catch
            (fn [error]
              (js/console.error error)
              {})))))

(defn fetch-speakerdeck
  [speakerdeck-url]
  (if speakerdeck-url
    (fetch-speakerdeck-oembed speakerdeck-url)
    nil))

(defn format-project
  [project]
  (let [fields (get project :properties)
        type (get-in fields [:type :select :name])
        vimeo-url (get-in fields [:vimeo-url :url])
        speakerdeck-url (get-in fields [:speakerdeck-url :url])]
    ;; Fetch these resources in parallel
    (p/let [[video speakerdeck] (p/all [(fetch-video vimeo-url)
                                        (fetch-speakerdeck speakerdeck-url)])]
      {:id         (get project :id)
       :uid        (get-in fields [:uid :formula :string])
       :pdfs       (->> (get-in fields [:pdf :files])
                        (map format-pdf))
       :thumbnail (->> (get-in fields [:thumbnail :files])
                       (map #(get-in % [:file :url]))
                       (first))
       :image      (->> (get-in fields [:image :files])
                        (map #(get-in % [:file :url]))
                        (first))
       :vimeo-url  vimeo-url
       :video      video
       :speakerdeck-url speakerdeck-url
       :speakerdeck speakerdeck
       :type       type
       :category   (get-in fields [:category :select :name])
       :tags       (->> (get-in fields [:tags :multi-select])
                        (map #(select-keys % [:id :name])))
       :featured   (get-in fields [:featured :checkbox])
       :title      (get-in fields [:name :title 0 :text :content])
       :updated-at (get project :last-edited-time)})))

(defn format-projects
  [projects]
  (->> projects
       (map format-project)
       (p/all)))

(defn fetch-videos
  [storyboards]
  (->> storyboards
       (map fetch-video)))

(defn type-order
  [[type _projects]]
  (case type
    "Storyboards"        0
    "Illustrations"      1
    "Sketchbook Samples" 2
    "Comics"             3
    99))

(defn sort-types
  [projects-by-type]
  (sort-by type-order projects-by-type))

(defn db->categories
  [db]
  (get-in db [:properties :category :select :options]))

(defn find-category
  [categories slug]
  (some #(when (= (u/slugify (:name %)) slug)
           (:name %)) categories))

(defn sort-newest-first
  [projects]
  (sort-by :updated-at #(compare %2 %1) projects))

(defn group-by-type
  [projects]
  (group-by :type projects))

(defn group-by-category
  [projects]
  (group-by :category projects))
