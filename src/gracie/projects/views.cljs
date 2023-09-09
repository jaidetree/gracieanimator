(ns gracie.projects.views
  (:require [framework.utils :as u]
            [cljs.pprint :refer [pprint]]))

(defn project-thumb
  [{:keys [url project]} & children]
  [:div.max-w-xs.w-full
   [:div.text-center
    [:div
     [:a.block
      {:href url}
      [:img.object-cover.h-64.w-full
       {:src (:thumbnail project)}]
      (into
        [:span.uppercase.text-lg.font-body.font-light
        children])]]]])
