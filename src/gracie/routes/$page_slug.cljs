(ns gracie.routes.$page-slug
  (:require
   [clojure.pprint :refer [pprint]]
   [promesa.core :as p]
   [framework.utils :as u]
   [notion.api :as notion]
   [notion.hiccup :refer [blocks->hiccup]]))


(defn loader
  [req {:keys [pages]}]
  (let [slug (get-in req [:params :page-slug])
        page (some #(when (= (:slug %) slug) %) pages)]
    (p/let [blocks (notion/fetch-all-blocks {:block-id (:id page)})]
      {:page page
       :blocks blocks})))

(defn view
  [req {:keys [page blocks] :as data}]
  [:div
   [:h1.mb-8 (:title page)]
   (-> [:div]
       (into (blocks->hiccup blocks)))
   #_[:pre
    (u/pprint-str data)]])
