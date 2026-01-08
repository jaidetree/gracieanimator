(ns gracie.projects2
  (:require
   [clojure.pprint :refer [pprint]]
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
             :checkbox {:equals true}}
    :sorts [{:property "Order"
             :direction "ascending"}]}))

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
           :block-id (get project :id)
           :title title
           :type  (keyword (slugify (str/lower-case type)))
           :slug   (str id "-" (slugify (str/lower-case title)))
           :order (get-in project [:properties :order :number]))))

(defn project-type?
  [project expected-type]
  (= (:type project) expected-type))

(defn featured?
  [project]
  (true? (:featured project)))

(defn find
  [f coll]
  (->> coll
       (filter f)
       (first)))

(defn group-by-type
  [sort-order projects]
  (->> sort-order
       (reduce
        (fn [pairs target-type]
          (let [project (find #(and (project-type? % target-type)
                                    (featured? %))
                              projects)]
            (if project
              (conj pairs [(name target-type) project])
              pairs)))
        [])))

(comment
  (group-by-type
   [:storyboards
    :illustrations
    :sketchbook-samples
    :comics]
   []))
