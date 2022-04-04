(ns gracie.projects.views
  (:require
   [framework.assets :refer [download-sync]]
   [framework.utils :as u]))

(defn project-thumb
  [{:keys [url project]} & children]
  [:div.max-w-xs.w-full
   [:div.text-center
    [:div.relative.overflow-hidden
     {:style {:height "13.5rem"}}
     [:a.absolute.left-0.right-0.top-0.bottom-0.block
      {:href url
       :style {:background-image (str "url('"
                                      (download-sync
                                       "imgs" (or (get project :thumbnail)
                                                  (get project :image)
                                                  (get-in project [:video :thumbnail_url]))
                                       (u/slugify (:title project)))
                                      "')")
               :background-repeat "no-repeat"
               :background-size   "cover"
               :background-position "center"}}]]
    [:h2.uppercase.text-lg.font-body.font-light
     (into
      [:a
       {:href url}]
      children)]]])
