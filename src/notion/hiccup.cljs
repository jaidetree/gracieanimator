(ns notion.hiccup
  (:require
   [clojure.string :as s]
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

(defn rich-text
  [text-entries]
  (for [{:keys [text annotations href]} text-entries]
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
    ))

(defn paragraph->p
  [{:keys [paragraph] :as block}]
  [:p.paragraph
   (rich-text (get paragraph :rich-text []) )])

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

(defn heading-1->h1
  [{:keys [heading-1] :as block}]
  [:h1.text-4xl
   (rich-text (get heading-1 :rich-text []))])

(defn heading-2->h2
  [{:keys [heading-2] :as block}]
  [:h1.text-2xl
   (rich-text (get heading-2 :rich-text []))])

(defn heading-3->h3
  [{:keys [heading-3] :as block}]
  [:h1.text-xl
   (rich-text (get heading-3 :rich-text []))])

(defn column-list->div-flex-row
  [{:keys [column-list] :as block}]
  [:div.flex.flex-row.justify-evenly.items-stretch.gap-4])

(defn column->div
  [{:keys [column] :as block}]
  [:div.flex-grow.flex-shrink])

(defn divider->hr
  [{:keys [divider] :as block}]
  [:hr.my-4])

(defn bulleted->li
  [{:keys [bulleted-list-item] :as block}]
  [:li
   (rich-text (get bulleted-list-item :rich-text []))])

(defn bulleted->ul
  [{:keys [bulleted-list] :as block}]
  [:ul.bullet-list.list-disc.list-outside.ml-4])

(defn numbered->ol
  [{:keys [numbered-list] :as block}]
  [:ol.number-list.list-decimal.list-outside.ml-4])

(defn numbered->li
  [{:keys [numbered-list-item] :as block}]
  [:li
   (rich-text (get numbered-list-item :rich-text []))])

(defn callout->aside
  [{:keys [callout] :as block}]
  [:div.p-4.text-lg.flex.flex-row.items-center
   {:class (case (keyword (get callout :color))
             :gray_background "bg-black bg-opacity-20")}
   [:span.text-2xl.mr-4
    (let [icon (get callout :icon)]
      (case (keyword (:type icon))
        :emoji (get icon :emoji)))]
   [:p
    (rich-text (get callout :rich-text []))]])

(defn code->pre
  [{:keys [code] :as block}]
  [:pre
   [:code
    {:class (str "language-" (get code :language))}
    (rich-text (get code :rich-text []))]])

(defn video->iframe
  [{:keys [video] :as block}]
  (let [type (keyword (:type video))]
    (if (= type :external)
      [:div.relative.my-8
       {:style {:padding-top "56%"}}
       [:iframe.absolute.left-0.right-0.top-0.bottom-0.w-full.h-full
        {:src   (get-in video [:external :url])}
        ]]
      [:video
       {:src (get-in video [:video :url])}])))

(defn pdf->iframe
  [{:keys [pdf] :as block}]
  (let [type (keyword (:type pdf))]
    (if (= type :file)
      [:div.relative.my-8
       {:style {:padding-top "77.27%"}}
       [:iframe.absolute.left-0.right-0.top-0.bottom-0.w-full.h-full
        {:src (get-in pdf [:file :url])}]
       ]
      [:div
       "PDF format currently unsupported. Please report this error"])))

(defn pdf-icon
  []
  [:svg {:xmlns "http://www.w3.org/2000/svg",
         :class "h-6 w-6",
         :fill "none",
         :viewbox "0 0 24 24",
         :stroke "currentColor",
         :stroke-width "2"}
   [:path {:stroke-linecap "round",
           :stroke-linejoin "round",
           :d "M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"}]])

(defn file->aside
  [{:keys [file] :as block}]
  [:aside.bg-black.bg-opacity-20
   (let [url-str (get-in file [:file :url])
         url (js/URL. url-str)]
     [:a.flex.flex-row.gap-4.p-4
      {:href url-str}
      [:span
       [pdf-icon]]
      [:span
       (.basename path (.-pathname url))]])])

(defn block->hiccup
  [block]
  (let [type (keyword (:type block))]
    (case type
      :paragraph          (paragraph->p block)
      :image              (image->img block)
      :heading_1          (heading-1->h1 block)
      :heading_2          (heading-2->h2 block)
      :heading_3          (heading-3->h3 block)
      :column_list        (column-list->div-flex-row block)
      :column             (column->div block)
      :divider            (divider->hr block)
      :bulleted_list      (bulleted->ul block)
      :bulleted_list_item (bulleted->li block)
      :numbered_list      (numbered->ol block)
      :numbered_list_item (numbered->li block)
      :callout            (callout->aside block)
      :code               (code->pre block)
      :video              (video->iframe block)
      :pdf                (pdf->iframe block)
      :file               (file->aside block)
      (do
        (println "Could not transform block into hiccup\n"
                 block)
        nil))))

(defn group-list-items
  [blocks]
  (if (empty? blocks)
    []
    (loop [blocks blocks
           grouped []
           last-type nil]
      (let [[block & remaining] blocks
            type (keyword (get block :type))]
        (if (or (nil? block) (empty? blocks))
          grouped
          (let [pair [last-type type]]
            (cond
              (:grouped block)
              (recur remaining
                     (conj grouped block)
                     type)

              (= pair [:bulleted_list_item :bulleted_list_item])
              (recur remaining
                     (update-in grouped [(dec (count grouped)) :children]
                                conj
                                (assoc block :grouped true))
                     type)

              (= (last pair) :bulleted_list_item)
              (recur remaining
                     (conj grouped {:type "bulleted_list"
                                    :bulleted-list {}
                                    :has-children true
                                    :children [(assoc block :grouped true)]})
                     type)

              (= pair [:numbered_list_item :numbered_list_item])
              (recur remaining
                     (update-in grouped [(dec (count grouped)) :children]
                                conj
                                (assoc block :grouped true))
                     type)

              (= (last pair) :numbered_list_item)
              (recur remaining
                     (conj grouped {:type "numbered_list"
                                    :numbered-list {}
                                    :has-children true
                                    :children [(assoc block :grouped true)]})
                     type)

              :else
              (recur remaining
                     (conj grouped block)
                     type))))))))

(defn blocks->hiccup
  [blocks]
  (->> blocks
       (group-list-items)
       (keep
        (fn [block]
          (let [el (block->hiccup block)
                children (:children block [])]
            (when el
              (if (:has-children block)
                (do
                 (into el (blocks->hiccup children)))
                el)))))))
