(ns gracie.projects2
  (:require
    [notion.api :as notion]
    [framework.env :as env]
    [gracie.queue :as q]))

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

