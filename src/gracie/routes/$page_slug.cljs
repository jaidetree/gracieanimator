(ns gracie.routes.$page-slug
  (:require
   [clojure.pprint :refer [pprint]]
   [clojure.string :as s]
   [promesa.core :as p]
   [framework.utils :as u]
   [notion.api :as notion]
   ["path" :as path]))

(defn annotations?
  [annotations]
  (-> annotations
      (select-keys [:bold :italic :strikethrough :underline])
      (vals)
      (set)
      (contains? true)))

(defn text-classes
  [{:keys [bold italic strikethrough underline]}]
  (s/trim
   (str
    (when bold " font-bold")
    (when italic " italic")
    (when strikethrough " line-through")
    (when underline " underline"))))

(defn paragraph->p
  [{:keys [paragraph] :as block}]
  [:p.paragraph
   (for [{:keys [text annotations href]} (get paragraph :rich-text [])]
     (let [content (get text :content "")]
       (cond
         href
         [:a
          {:href (get-in text [:link :url])
           :class (text-classes annotations)}
          content]

         (:code annotations)
         [:code
          {:class (text-classes annotations)}
          content]

         (annotations? annotations)
         [:span
          {:class (text-classes annotations)}
          content]

         :else
         content))
     )])

(defn img
  [{:keys [image url]}]
  (let [caption (->> image
                     (:caption)
                     (map #(get-in % [:text :content]))
                     (s/join " "))]
    [:img
     {:src url
      :alt (if (s/blank? caption)
             (let [basename (.basename path url)]
               (subs (.basename path url) 0 (s/index-of basename "?")))
             caption)}]))

(defn image->img
  [{:keys [image] :as block}]
  (let [type (keyword (:type image))]
    (case type
      :external [img
                 {:url (get-in image [:external :url])
                  :image image}]
      :file     [img
                 {:url (get-in image [:file :url])
                  :image image}])))

(defn block->hiccup
  [block]
  (let [type (keyword (:type block))]
    (println type)
    (case type
      :paragraph (paragraph->p block)
      :image (image->img block)
      (do
        (println "Could not transform block into hiccup\n"
                 block)
        nil))))

(defn notion->hiccup
  [blocks]
  (->> blocks
       (keep
        (fn [block]
          (let [el (block->hiccup block)
                children (:children block [])]
            (when el
              (if (count children)
                (into el (notion->hiccup children))
                el)))))))

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
       (into (notion->hiccup blocks)))
   #_[:pre
    (u/pprint-str data)]])
