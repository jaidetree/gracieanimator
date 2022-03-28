(ns notion.api
  (:require
   [clojure.string :as s]
   [cljs-bean.core :refer [->js bean]]
   [promesa.core :as p]
   [framework.env :as env]
   [framework.utils :refer [slugify]]
   ["fs" :as fs]))

(def notion-api (js/require "@notionhq/client"))
(def api-key (env/required :NOTION_API_KEY))

(def notion (new (.-Client notion-api) #js {:auth api-key}))

(def key-fn (comp keyword slugify))

(defn js->clj-slugify
  [v]
  (cond
    (object? v) (into {}
                      (map (fn [[k v]]
                             [(key-fn k) (js->clj-slugify v)]))
                      (js/Object.entries v))
    (array? v) (mapv #(js->clj-slugify %) v)
    :else v))


(defn fetch-page
  [{:keys [page-id]}]
  (p/-> (.. notion -pages (retrieve #js {:page_id page-id}))
        (js->clj-slugify)))

(defn fetch-blocks
  [{:keys [block-id]}]
  (p/-> (.. notion -blocks -children (list #js {:block_id block-id}))
        (js->clj-slugify)
        (get :results [])))

(defn fetch-all-blocks
  [{:keys [block-id]}]
  (p/let [blocks (fetch-blocks {:block-id block-id})]
    (p/-> (p/all (->> blocks
                      (filter #(not (:archived %)))
                      (map #(if (true? (:has-children %))
                              (p/let [blocks (fetch-all-blocks {:block-id (:id %)})]
                                (assoc % :children blocks))
                              (p/resolved (assoc % :children []))))
                      (vec)))
          (js->clj-slugify))))

(defn write-json-file
  [filename text]
  (.writeFileSync fs filename text #{:encoding "utf-8"}))

(defn append-blocks
  [{:keys [block-id children]}]
  (let [children (->js children)]

    (write-json-file
     "request.json"
     (js/JSON.stringify #js {:block-id "[redacted]"
                             :children children} nil 2))
    (p/let [response (.. notion -blocks -children
                         (append #js {:block_id block-id
                                      :children children}))]
      (-> response
          (js->clj-slugify)
          (get :results [])))))


(defn fetch-db-entries
  [{:keys [db-id filter sorts]}]
  (let [request (clj->js
                 (merge
                  {:database_id db-id}
                  (when filter {:filter filter})
                  (when sorts {:sorts sorts}))
                   )]
    (p/let [pages (.. notion -databases (query request))]
      (-> pages
          (js->clj-slugify)
          (get :results [])))))

(defn fetch-db
  [{:keys [db-id]}]
  (let [request (clj->js {:database_id db-id})]
    (p/let [db (.. notion -databases (retrieve request))]
      (-> db
          (js->clj-slugify)))))
