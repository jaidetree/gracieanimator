(ns gracie.projects2
  (:require
    [clojure.string :as str]
    [notion.api :as notion]
    [framework.env :as env]
    [gracie.queue :as q]
    [framework.utils :refer [slugify]]))


(defn fetch-projects
  []
  (notion/fetch-db-entries
    {:db-id (env/required "CMS_STORYBOARDS_ID"),
     :filter {:property "Published",
              :checkbox {:equals true}}}))

(defn enqueue-projects
  []
  (q/enqueue
    {:type :resource
     :requests [{:id "notion-projects"
                 :fetch fetch-projects
                 :reducer (fn [_ctx projects]
                            projects)}]}))

(defn normalize
  [project]
  (let [type (get-in project [:properties :type :select :name])
        id (get-in project [:properties :id :unique-id :number])
        title (get-in project [:properties :name :title 0 :text :content])]
    (assoc project
           :id    id
           :title title
           :type  (keyword (slugify (str/lower-case type)))
           :slug   (str id "-" (slugify (str/lower-case title))))))
