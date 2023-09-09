(ns gracie.pages
  (:require
    [promesa.core :as p]
    [notion.api :as notion]
    [notion.hiccup :refer [blocks->hiccup]]
    [gracie.queue :as q]
    [framework.env :as env]
    [framework.stream :as stream]))

(defn normalize-page
  [page]
  (let [props (get page :properties {})]
    {:id    (get page :id),
     :slug  (get-in props [:url-friendly-name :rich-text 0 :text :content]),
     :title (get-in props [:name :title 0 :text :content])
     :type  :pages}))

(defn fetch-pages
  []
  (-> (stream/from-promise
        (notion/fetch-db-entries
           {:db-id (env/required "CMS_PAGES_ID")
            :filter {:and [{:property "Published"
                            :checkbox {:equals true}}]}
            :sorts [{:property "Order"
                     :direction "ascending"}]}))
      (.flatMap stream/from-seq)
      (.map normalize-page)
      (.flatMap
        (fn [page]
          (stream/from-promise
            (p/let [blocks (notion/fetch-blocks
                             {:block-id (:id page)})]
              (assoc page
                     :content (if (seq blocks)
                                (blocks->hiccup blocks)
                                []))))))
      (.reduce [] conj)
      (.toPromise)))


(defn enqueue-pages
  []
  (q/enqueue
    {:type :resource
     :requests [{:id      "notion-pages"
                 :fetch   fetch-pages
                 :reducer (fn [_ctx pages]
                            pages)}]}))

