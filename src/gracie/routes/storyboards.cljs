(ns gracie.routes.storyboards
  (:require
    [gracie.projects2 :as projects]
    [gracie.projects.views :refer [project-thumb]]
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

(def category-view
  (require-password
    (fn [req {:keys [projects]}]
      [:div "Storyboard Category"])))

(defn projects->categories
  [projects]
  (->> projects
       (filter #(projects/project-type? % :storyboards))
       (group-by :category)))

(def index-view
  (require-password
    (fn [req {:keys [projects]}]
      (let [categories (projects->categories projects)]
        [:main
         [:h1.text-center.md:text-left "Storyboards"]
         [:div.space-y-16
          (for [[category storyboards] categories]
           [:section.mt-8
            {:key category}
            [:header.text-center.md:text-left
             [:h2
              [:a
               {:href (str "/storyboards/category/" (u/slugify category))}
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

(def single-view
  (require-password
    (fn [req {:keys [projects]}]
      [:div "Single Storyboard View"])))
