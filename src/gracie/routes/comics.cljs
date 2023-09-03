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
         [:a.col-span-4.text-center
          {:key (:slug comic)
           :href (str "/comics/" (:slug comic) "/")}
          [:img.object-scale-down.h-80.m-auto
           {:src (:thumbnail comic)
            :alt (:title comic)}]
          [:span.font-body.font-light.text-lg.uppercase
           (:title comic)]])]]}))

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

(defn single-view
 [req {:keys [projects]}]
 (let [slug (get-in req [:params :slug])
       comics (->> projects
                   (filter #(projects/project-type? % :comics)))
       {:keys [comic prev next]} (select-comic comics slug)]
   {:status 200
    :session (:session req)
    :title (str (:title comic) " | Comics")
    :view
    [:div.comic
      [:hgroup
        [:a.inline-block.mb-2.uppercase.font-light
         {:href "/comics/"}
         "← comics"]
        [:h1.mb-8 (:title comic)]]
      [:img.mb-8.mx-auto
       {:class "w-[80%] h-auto"
        :src (:image-url comic)
        :alt (:title comic)}]
      [:div.flex.flex-row.justify-between.p-4
       {:class "bg-black/10"}
       [:a.flex.flex-row.items-center.gap-2
        {:href (str "/comics/" (:slug prev) "/")}
        [:img.object-scale-down.h-20
         {:src (:thumbnail prev)
          :alt (:title prev)}]
        [:span.text-lg.font-bold.uppercase
         "prev:"]
        (:title prev)]
       [:a.flex.flex-row.items-center.gap-2
        {:href (str "/comics/" (:slug next) "/")}
        [:span.text-lg.font-bold.uppercase
          "next"]
        (:title next)
        [:img.object-scale-down.h-20
         {:src (:thumbnail next)
          :alt (:title next)}]]]]}))

