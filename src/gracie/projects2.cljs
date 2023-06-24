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
     :requests [{:url "notion-projects"
                 :fetch (fn [_url]
                          (fetch-projects))}]}))

(defn normalize
  [project]
  (let [type (get-in project [:properties :type :select :name])]
    (assoc project :type (keyword (slugify (str/lower-case type))))))

