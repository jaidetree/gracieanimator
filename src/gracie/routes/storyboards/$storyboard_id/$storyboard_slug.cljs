(ns gracie.routes.storyboards.$storyboard-id.$storyboard-slug
  (:require
   [clojure.pprint :refer [pprint]]
   [promesa.core :as p]
   [framework.assets :refer [download-sync]]
   [framework.env :as env]
   [framework.utils :as u]
   [notion.api :as notion]
   [notion.hiccup :refer [blocks->hiccup]]
   [gracie.projects.core :as projects]
   [clojure.string :as s]))

(defn pdf-icon
  []
  [:svg {:xmlns "http://www.w3.org/2000/svg",
         :class "h-6 w-6",
         :fill "none",
         :viewBox "0 0 24 24",
         :stroke "currentColor",
         :stroke-width "2"}
   [:path {:stroke-linecap "round",
           :stroke-linejoin "round",
           :d "M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"}]])

(defn img-icon
  []
  [:svg {:xmlns "http://www.w3.org/2000/svg",
         :class "h-6 w-6",
         :fill "none",
         :viewBox "0 0 24 24",
         :stroke "currentColor",
         :stroke-width "2"}
   [:path {:stroke-linecap "round",
           :stroke-linejoin "round",
           :d "M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"}]])

(defn loader
  [req _data]
  (let [uid (-> req
                (get-in [:params :storyboard-id])
                (u/base64->uid))]
    (p/let [storyboard
            (p/->> (notion/fetch-db-entries
                    {:db-id (env/required "CMS_STORYBOARDS_ID")
                     :filter {:and [{:property "Published"
                                     :checkbox {:equals true}}
                                    {:property "UID"
                                     :formula {:string {:equals uid}}}
                                    ]}})
                   (first)
                   (projects/format-project))
            blocks (notion/fetch-all-blocks {:block-id (:id storyboard)})]
      {:storyboard storyboard
       :blocks blocks
       :id uid
       :slug (get-in req [:params :storyboard-slug])})))


(defn view
  [req {:keys [storyboard id slug blocks]}]
  [:div
   #_[:div#login-page
    [:form.max-w-xl.m-auto
     {:method "POST"
      :action "/.netlify/functions/login"}
     [:input.bg-white.bg-opacity-20.px-4.text-lg.text-white.w-full
      {:type "password"
       :name "password"}]
     [:div.text-center
      [:button
       {:type "submit"}
       "Login"]]]]

   [:div#storyboard-page.grid.grid-cols-12.gap-8
    [:main.col-span-full.md:col-span-8.space-y-16.order-2.md:order-1
     [:div#animatic.space-y-8
      [:h1
       (:title storyboard)]
      [:div.embedded-video.relative.md:block
       {:style (let [video (get storyboard :video {})
                     {:keys [width height]} video]
                 {:padding-bottom (-> height
                                      (/ width)
                                      (* 100)
                                      (str "%"))})
        :dangerouslySetInnerHTML {:__html (s/replace
                                           (get-in storyboard [:video :html])
                                           #"<iframe"
                                           "<iframe class=\"absolute w-full h-full top-0 left-0\"")}}]]

     (when (:speakerdeck storyboard)
       [:div#boards.space-y-8
        [:h2
         "Boards"]
        [:div.embedded-shots.relative.md:block
         {:style (let [deck (get storyboard :speakerdeck {})
                       {:keys [width height]} deck]
                   {:padding-bottom (-> height
                                        (/ width)
                                        (* 100)
                                        (str "%"))})

          :dangerouslySetInnerHTML
          {:__html (s/replace (get-in storyboard [:speakerdeck :html])
                              #"<iframe"
                              "<iframe class=\"absolute w-full h-full top-0 left-0\"")}}]])

     (when (pos? (count (get storyboard :pdfs [])))
       [:div#pdfs.space-y-8
        [:h2
         "PDFs"]
        [:ul.bg-black.bg-opacity-20.p-8.md:block
         (for [pdf (get storyboard :pdfs [])]
           [:li
            {:key (:name pdf)}
            [:a.flex.flex-row
             {:href (:url pdf)
              :target (str "_grace_pdf_")}
             [:span.mr-2.text-lg
              [pdf-icon]]
             (:name pdf)]])]])

     (when (count blocks)
       [:div#content.space-y-8
        (blocks->hiccup blocks)])


     #_[:pre
      (u/pprint-str (get storyboard :speakerdeck))]

     ]

    [:aside.col-span-12.md:col-span-4.order-1.md:order-2
     [:div.space-y-4.sticky.top-8
      [:div.sidebar-section
       [:h2 "Category"]
       [:a
        {:href (str "/storyboards")}
        "Storyboards"]
       [:span.mx-4.text-white.text-opacity-50 "/"]
       [:a
         {:href (str "/storyboards/category/" (u/slugify (:category storyboard)))}
         (:category storyboard)]]

      [:div.sidebar-section
       [:h2 "Navigation"]
       [:ul.border-l-2.border-white.ml-4
        [:li
         [:a.py-1.px-4.block.text-white.text-opacity-80.hover:text-opacity-100.hover:bg-black.hover:bg-opacity-20
          {:href "#animatic"}
          "Animatic"]]
        (when (get storyboard :speakerdeck)
          [:li
           [:a.py-1.px-4.block.text-white.text-opacity-80.hover:text-opacity-100.hover:bg-black.hover:bg-opacity-20
            {:href "#boards"}
            "Boards"]])
        (when (seq (get storyboard :pdfs []))
          [:li
           [:a.py-1.px-4.block.text-white.text-opacity-80.hover:text-opacity-100.hover:bg-black.hover:bg-opacity-20
            {:href "#pdfs"}
            "PDFs"]])
        (when (seq blocks)
          [:li
           [:a.py-1.px-4.block.text-white.text-opacity-80.hover:text-opacity-100.hover:bg-black.hover:bg-opacity-20
            {:href "#content"}
            "More"]])
        ]]

      (when (count (get storyboard :pdfs []))
        [:div.sidebar-section
         [:h2 "Quick Links"]
         [:ul.space-y-1
          (when-let [deck (storyboard :speakerdeck)]
            [:li
             [:a.flex.flex-row.gap-2
              {:href (get storyboard :speakerdeck-url)}
              [:span
               [img-icon]]
              "Boards"]])
          (for [pdf (get storyboard :pdfs [])]
            [:li
             {:key (:name pdf)}
             [:a.flex.flex-row.gap-2
              {:href (download-sync "downloads" (:url pdf))}
              [:span
               [pdf-icon]]
              (:name pdf)]])]])]]]


   [:script {:src "/js/login-gate.js"}]]
  )
