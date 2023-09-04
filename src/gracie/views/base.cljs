(ns gracie.views.base
  (:require [framework.utils :refer [pprint-str]]))

(defn site-header
  [{:keys [pages]}]
  [:div.md:flex.md:flex-row.justify-between.items-center.mb-8.md:mb-16.site-header
   [:h1.site-title.text-center.md:text-left [:a {:href "/"} "The Grace Space"]]
   [:nav.flex.flex-row.gap-4.site-nav.justify-center.md:justify-start
    [:a {:href "/"} "Portfolio"]
    (for [{:keys [slug title]} pages]
      [:a {:key slug, :href (str "/" slug "/")} title])]])

(defn base
  [req {:keys [pages]} & children]
  [:html
   [:head
    [:meta {:name "viewport", :content "width=device-width, initial-scale=1.0"}]
    [:title (if (:title req)
              (str (:title req) " | Grace Space")
              "Grace Space")]
    [:link {:rel "preconnect", :href "https://fonts.googleapis.com"}]
    [:link
     {:rel "preconnect",
      :href "https://fonts.gstatic.com",
      :crossOrigin "true"}]
    [:script
     {:src "https://cdn.jsdelivr.net/npm/scittle@0.6.15/dist/scittle.js"
      :type "application/javascript"}]
    [:link
     {:rel "stylesheet",
      :href
        "https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,300;1,400;1,500;1,600;1,700;1,800&family=Work+Sans:ital,wght@0,100;0,300;0,400;0,600;0,700;0,800;1,400&display=block"}]
    [:link {:rel "stylesheet", :href "/css/stylesheet.css"}]]
   (when-let [meta-seq (seq (:meta req))]
     (for [[idx meta-props] (map-indexed vector meta-seq)]
       ^{:key idx} [:meta meta-props]))
   (when-let [script-seq (seq (:scripts req))]
     (for [[idx script] (map-indexed vector script-seq)]
       ^{:key idx} [:script
                    (merge {:type (or (:type script) "application/x-scittle")}
                           (when (:src script)
                             {:src (:src script)}))
                    (if (:content script)
                      (:content script)
                      "")]))
   [:body.bg-primary.text-white
    [:div.max-w-5xl.m-auto.my-8.p-4.md:p-0.md:my-16 [site-header {:pages pages}]
     (-> [:div.page]
         (into children))]]])



(defn error-404
  [req data]
  [base req data
   [:section [:h1 "404 Not Found"]
    [:p
     "The requested URL could not be found. Maybe try a little harder next time ok champ?"]]])

(defn error-505
  [req {:keys [error], :as data}]
  [base req data
   [:section [:h1 "Hey it's a.. uh... \"oh no\""]
    [:pre (str (ex-message error) "\n" (pprint-str (ex-data error)))]]])

(def status-pages {404 #'error-404, 500 #'error-505})
