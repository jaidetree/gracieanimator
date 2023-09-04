(ns gracie.routes.comics
  (:require
    [clojure.pprint :refer [pprint]]
    [gracie.projects2 :as projects]))

(defn index-view
  [req {:keys [projects]}]
  (let [comics (->> projects
                    (filter #(projects/project-type? % :comics)))]
    {:status 200
     :session (:session req)
     :title "Comics"
     :view
     [:div [:h1.mb-8 "Comics"]
      [:div.comics.grid.grid-cols-12.gap-8
       (for [comic comics]
         [:div.col-span-6.text-center
          {:key (:slug comic)
           :class "bg-black/10 p-4"}
          [:a.text-center.block
           {:href (str "/comics/" (:slug comic) "/")}
           [:img.w-auto.mx-auto
            {:class "h-[42rem]"
             :src (:thumbnail comic)
             :alt (:title comic)}]
           [:span.font-body.font-light.text-lg.uppercase.my-2
            (:title comic)]]
          [:div.grid.grid-cols-12.gap-2
           (for [[idx page] (rest (map-indexed vector (:pages comic)))]
             [:a.col-span-3.opacity-50.hover:opacity-100
              {:key page
               :href (str "/comics/" (:slug comic) "/page/" (inc idx) "/")}
              [:img.object-scale-down.w-full
               {:src page
                :alt page}]])]])]]}))

(defn wrap-forward
  [idx last-idx]
  (if (> idx last-idx)
    0
    idx))

(defn wrap-backward
  [idx last-idx]
  (if (>= idx 0)
    idx
    last-idx))


(defn select-comic
  [comics slug]
  (let [[idx comic] (->> comics
                         (keep-indexed
                           (fn [idx comic]
                             (when (= (:slug comic) slug)
                               [idx comic])))
                         (first))
        last-idx (dec (count comics))
        prev-idx (wrap-backward (dec idx) last-idx)
        next-idx (wrap-forward  (inc idx) last-idx)]
    {:comic comic
     :prev (nth comics prev-idx)
     :next (nth comics next-idx)}))

(comment
  (mod 3 2))

(defn prev-link
  [{:keys [slug current-page pages]}]
  (let [page-num (dec current-page)]
    [:a.fixed.top-0.bottom-0.left-4.lg:left-20.m-auto.w-12.h-12.z-10.rounded-full
      {:class (str
                "bg-black/10 lg:bg-transparent"
                (when-not (< 0 page-num)
                  " hidden"))
       :id "prev-comic"
       :href (if (= page-num 1)
               (str "/comics/" slug "/")
               (str "/comics/" slug "/page/" page-num "/"))}
      [:svg.pointer-events-none
       {:xmlns "http://www.w3.org/2000/svg",
        :fill "none",
        :viewBox "0 0 24 24",
        :strokeWidth "1.5",
        :stroke "currentColor",
        :class "w-full h-full"}
       [:path
         {:strokeLinecap "round",
          :strokeLinejoin"round",
          :d "M15.75 19.5L8.25 12l7.5-7.5"}]]]))

(defn next-link
  [{:keys [slug current-page pages]}]
  (let [page-num (inc current-page)]
    [:a.fixed.top-0.bottom-0.right-4.lg:right-20.m-auto.w-12.h-12.z-10.rounded-full
      {:class (str
                "bg-black/10 lg:bg-transparent"
               (when-not (<= page-num (count pages))
                 " hidden"))
       :id "next-comic"
       :href (str "/comics/" slug "/page/" page-num "/")}
      [:svg.pointer-events-none
       {:xmlns "http://www.w3.org/2000/svg",
        :fill "none",
        :viewBox "0 0 24 24",
        :strokeWidth "1.5",
        :stroke "currentColor",
        :class "w-full h-full"}
       [:path
        {:strokeLinecap "round",
         :strokeLinejoin "round",
         :d "M8.25 4.5l7.5 7.5-7.5 7.5"}]]]))

(defn single-view
 [req {:keys [projects]}]
 (let [slug (get-in req [:params :slug])
       current-page (js/Number (get-in req [:params :page] 1))
       comics (->> projects
                   (filter #(projects/project-type? % :comics)))
       {:keys [comic prev next]} (select-comic comics slug)]
   {:status 200
    :session (:session req)
    :title (str (:title comic) " | Comics")
    :scripts [{:src "/cljs/comics.cljs"}]
    :view
    [:div.comic
      [:hgroup
        [:a.inline-block.mb-2.uppercase.font-light
         {:href "/comics/"}
         "← comics"]
        [:h1.mb-8 (:title comic)]]
      [:div.relative.m-auto
       {:id "comic-ui"
        :class "w-[80%] lg:w-full"}
       [:img.mb-8.mx-auto.w-full
        {:class "h-auto"
         :id    "comic-viewer"
         :src (get-in comic [:pages (dec current-page)])
         :alt (:title comic)}]
       [prev-link
        {:slug slug
         :current-page current-page
         :pages (:pages comic)}]
       [next-link
        {:slug slug
         :current-page current-page
         :pages (:pages comic)}]]
      [:div.grid.grid-cols-12.gap-2.mx-auto
       {:id "comic-pages"}
       (for [[idx page-url] (map-indexed vector (:pages comic))]
         (let [page-num (inc idx)]
           [:a.block.col-span-3.hover:opacity-100.comic-page
            {:key page-url
             :class (if (= page-num current-page)
                      "opacity-100 selected"
                      "opacity-50")
             :href (if (= page-num 1)
                     (str "/comics/" (:slug comic) "/")
                     (str "/comics/" (:slug comic) "/page/" page-num "/"))}
            [:img.object-scale-down.w-full
             {:src page-url
              :alt (cond-> (str "Comic " (:title comic))
                     (> page-num 1) (str " page " page-num))}]]))]
      [:div.lg:flex.lg:flex-row.justify-between.p-4.mt-8
       {:class "bg-black/10"}
       [:a.flex.flex-row.items-center.gap-2
        {:href (str "/comics/" (:slug prev) "/")}
        [:img.object-scale-down.h-20
         {:src (:thumbnail prev)
          :alt (:title prev)}]
        [:span.flex.flex-col.lg:flex-row.flex-grow.lg:flex-initial.lg:items-center.gap-2         [:span.text-lg.font-bold.uppercase
                                                                                                  "prev:"]
         (:title prev)]]
       [:a.flex.flex-row.items-center.gap-2
        {:href (str "/comics/" (:slug next) "/")}
        [:span.flex.flex-col.lg:flex-row.flex-grow.lg:flex-initial.lg:items-center.gap-2
         [:span.text-lg.font-bold.uppercase
           "next:"]
         (:title next)]
        [:img.object-scale-down.h-20
         {:src (:thumbnail next)
          :alt (:title next)}]]]]}))

;; IDEAS
;; - Show the grid of comics below with this comic omitted
;; - Use client-side code to replace the main image for faster nav
;; - Cache responses with ring middleware. It can take cache strategies
;;   so storyboard pages can be treated differently depending on auth
