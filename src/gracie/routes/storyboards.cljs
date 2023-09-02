(ns gracie.routes.storyboards
  (:require
    [clojure.string :as s]
    [gracie.projects2 :as projects]
    [gracie.projects.views :refer [project-thumb]]
    [notion.hiccup :refer [blocks->hiccup]]
    [framework.utils :as u]))

(defn login-view
  [req {:keys []}]
  [:div.login
   [:form
    {:action "/auth/"
     :method "POST"}
    [:input
     {:type "hidden"
      :name "csrf"
      :value (get-in req [:session :csrf])}]
    [:input
     {:type "hidden"
      :name "redirect"
      :value (:path req)}]
    [:h2.text-center.mb-4
     "This page is password protected"]
    [:div.md:flex.md:flex-row.gap-2.max-w-md.m-auto
     [:input.bg-black.bg-opacity-20.px-4.py-2.text-xl.text-white.w-full.rounded-sm.placeholder:text-white.placehoder:text-opacity-75
      {:type "password"
       :placeholder "password"
       :name "password"}]
     [:button.text-white.border-white.border.rounded-sm.px-4.py-2.text-sm
      {:type "submit"
       :name "submit_btn"}
      "Login"]]]])


(defn require-password
  [view-fn]
  (fn [req data]
    (let [authenticated (get-in req [:session :auth])]
      (if authenticated
        (view-fn req data)
        (login-view req data)))))

(defn group-by-category
  [projects]
  (->> projects
       (filter #(projects/project-type? % :storyboards))
       (group-by :category)
       (map (fn [[category storyboards]]
              [(u/slugify category) {:category category
                                     :storyboards storyboards}]))
       (into {})))

(def category-view
  (require-password
    (fn [req {:keys [projects]}]
      (let [categories (group-by-category projects)
            category-slug (get-in req [:params :category-slug])
            {:keys [category storyboards]} (get categories category-slug)]
        [:main
         [:h1.text-center.md:text-left
          [:a
           {:href "/storyboards/"}
           "Storyboards"]
          [:span.mx-4.font-thin "/"]
          category]
         [:div.space-y-16
          [:section.mt-8
           {:key category}
           [:ul.flex.flex-wrap.gap-4.mt-8.justify-center.md:justify-start
            (for [storyboard storyboards]
              (let [url (str "/storyboards/"
                             (:slug storyboard))]
                [:li.max-w-xs.w-full
                 {:key url}
                 [project-thumb
                  {:project storyboard
                   :url url}
                  (:title storyboard)]]))]]]]))))

(def index-view
  (require-password
    (fn [req {:keys [projects]}]
      (let [categories (group-by-category projects)]
        [:main
         [:h1.text-center.md:text-left "Storyboards"]
         [:div.space-y-16
          (for [[slug {:keys [category storyboards]}] categories]
           [:section.mt-8
            {:key category}
            [:header.text-center.md:text-left
             [:h2
              [:a
               {:href (str "/storyboards/category/" slug)}
               category]]]
            [:ul.flex.flex-wrap.gap-4.mt-8.justify-center.md:justify-start
             (for [storyboard storyboards]
               (let [url (str "/storyboards/"
                              (:slug storyboard))]
                 [:li.max-w-xs.w-full
                  {:key url}
                  [project-thumb
                   {:project storyboard
                    :url url}
                   (:title storyboard)]]))]])]]))))


(defn pdf-icon
  []
  [:svg
   {:xmlns "http://www.w3.org/2000/svg",
    :class "h-6 w-6",
    :fill "none",
    :viewBox "0 0 24 24",
    :stroke "currentColor",
    :stroke-width "2"}
   [:path
    {:stroke-linecap "round",
     :stroke-linejoin "round",
     :d
       "M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"}]])

(defn img-icon
  []
  [:svg
   {:xmlns "http://www.w3.org/2000/svg",
    :class "h-6 w-6",
    :fill "none",
    :viewBox "0 0 24 24",
    :stroke "currentColor",
    :stroke-width "2"}
   [:path
    {:stroke-linecap "round",
     :stroke-linejoin "round",
     :d
       "M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"}]])

(defn vimeo-video
  [storyboard]
  [:div.embedded-video.relative.md:block
   {:style (let [video (get storyboard :vimeo {})
                 {:keys [width height]} video]
             {:padding-bottom (-> height
                                  (/ width)
                                  (* 100)
                                  (str "%"))}),
    :dangerouslySetInnerHTML
    {:__html
     (s/replace
       (get-in storyboard [:vimeo :html] "")
       #"<iframe"
       "<iframe class=\"absolute w-full h-full top-0 left-0\"")}}])

(defn speakerdeck
  [deck]
  [:div.embedded-shots.relative.md:block
   {:style (let [{:keys [width height]} deck]
             {:padding-bottom (-> height
                                  (/ width)
                                  (* 100)
                                  (str "%"))}),
    :dangerouslySetInnerHTML
    {:__html
     (s/replace
       (get deck :html "")
       #"<iframe"
       "<iframe class=\"absolute w-full h-full top-0 left-0\"")}}])

(defn pdf-item
  [pdf]
  [:li
   [:a.flex.flex-row
    {:href (:url pdf)
     :target (str "_grace_pdf_")}
    [:span.mr-2.text-lg [pdf-icon]]
    (:name pdf)]])

(defn category
  [storyboard]
  (let [cat (:category storyboard)]
    [:div.sidebar-section
     [:h2 "Category"]
     [:a {:href (str "/storyboards")} "Storyboards"]
     [:span.mx-4.text-white.text-opacity-50 "/"]
     [:a
      {:href (str "/storyboards/category/" (u/slugify cat) "/")}
      cat]]))

(defn nav-link
  [{:keys [id]} & children]
  [:li
   (into
     [:a.py-1.px-4.block.text-white.text-opacity-80.hover:text-opacity-100.hover:bg-black.hover:bg-opacity-20
      {:href (str "#" id)}]
     children)])

(defn navigation
  [& children]
  [:div.sidebar-section
   [:h2 "Navigation"]
   (into
     [:ul.border-l-2.border-white.ml-4]
     children)])

(defn quick-link
  [{:keys [href icon]} child]
  [:li
   [:a.flex.flex-row.gap-2
    {:href href}
    [:span [icon]]
    child]])

(defn quick-links
  [storyboard]
  [:div.sidebar-section
   [:h2 "Quick Links"]
   [:ul.space-y-1
    (for [[idx deck] (map-indexed vector (get storyboard :speakerdecks))]
      [quick-link
       {:href (:url deck)
        :icon img-icon
        :key idx}
       (str "Boards Set " (inc idx))])
    (for [pdf (get storyboard :pdfs)]
      [quick-link
       {:key (:name pdf)
        :href (:url pdf)
        :icon pdf-icon}
       (:name pdf)])]])

(def single-view
  (require-password
    (fn [req {:keys [projects]}]
      (let [storyboard-slug (get-in req [:params :storyboard-slug])
            storyboard (->> projects
                           (filter #(= (:slug %) storyboard-slug))
                           (first))
            blocks (seq (get storyboard :blocks))
            speakerdecks (seq (get storyboard :speakerdecks))
            pdfs (seq (get storyboard :pdfs))]
        [:div
         [:div#storyboard-page.grid.grid-cols-12.gap-8
          [:main.col-span-full.md:col-span-8.space-y-16.order-2.md:order-1
           [:div#animatic.space-y-8 [:h1 (:title storyboard)]
            [vimeo-video storyboard]]
           (when speakerdecks
             [:div#boards.space-y-8 [:h2 "Boards"]
              (for [[idx deck] (map-indexed vector speakerdecks)]
                ^{:key idx} [speakerdeck deck])])
           (when pdfs
             [:div#pdfs.space-y-8 [:h2 "PDFs"]
              [:ul.bg-black.bg-opacity-20.p-8.md:block
               (for [pdf pdfs]
                 ^{:key (:name pdf)} [pdf-item pdf])]])
           (when blocks
             [:div#content.space-y-8 (blocks->hiccup blocks)])]
          [:aside.col-span-12.md:col-span-4.order-1.md:order-2
           [:div.space-y-4.sticky.top-8
            [category storyboard]
            (when (or speakerdecks
                      pdfs
                      blocks)
             [navigation
              (when speakerdecks
                [nav-link {:id "boards"} "Boards"])
              (when (seq (get storyboard :pdfs))
                [nav-link {:id "pdfs"} "PDFs"])
              (when blocks
                [nav-link {:id "content"} "More"])])
            (when (or speakerdecks pdfs)
              [quick-links storyboard])]]]]))))



