(ns gracie.views.base
  (:require
   [framework.utils :refer [pprint-str]]))

(defn site-header
  []
  [:div.flex.flex-row.justify-between.items-center.mb-16
   [:h1.site-title
    [:a {:href "/"}
     "The Grace Space"]]
   [:nav.flex.flex-row.gap-4.site-nav
    [:a {:href "/portfolio"} "Portfolio"]
    [:a {:href "/resume"} "Resume"]
    [:a {:href "/about"} "About"]]])

(defn base
  [req data & children]
  [:html
   [:head
    [:title "Grace Space"]
    [:link {:rel "preconnect" :href "https://fonts.googleapis.com"}]
    [:link {:rel "preconnect" :href "https://fonts.gstatic.com" :crossOrigin "true"}]
    [:link {:rel "stylesheet" :href "https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,300;1,400;1,500;1,600;1,700;1,800&family=Work+Sans:ital,wght@0,100;0,300;0,400;0,600;0,700;0,800;1,400&display=block"}]
    [:link {:rel "stylesheet" :href "/css/stylesheet.css"}]]
   [:body.bg-primary.text-white
    (-> [:main.max-w-5xl.m-auto.my-16
         [site-header]]
        (into children))]])


(defn error-404
  [req data]
  [base
   req data
   [:section
    [:h1 "404 Not Found"]
    [:p "The requested URL could not be found. Maybe try a little harder next time ok champ?"]]])

(defn error-505
  [req {:keys [error] :as data}]
  [base
   req data
   [:section
    [:h1 "Hey it's a.. uh... \"oh no\""]
    [:pre
     (str
      (ex-message error) "\n"
      (pprint-str (ex-data error)))]]])

(def status-pages
  {404 #'error-404
   500 #'error-505})
